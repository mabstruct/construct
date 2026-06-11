"""LangGraph L2 gate for grounded Q&A with citations (tranche 1)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


# ── State schema (TypedDict — LangGraph prefers this over BaseModel) ──


class AskDomainState(TypedDict):
    # Input (set before graph starts)
    question: str
    domain_id: str
    workspace_path: str
    max_cards: int

    # Processing (populated by nodes)
    cards: list[dict]  # Loaded and filtered KnowledgeCard dicts
    context: str  # Formatted card summaries for LLM prompt
    provider: str  # Resolved provider name
    model: str  # Resolved model name

    # LLM output
    synthesised_answer: str | None
    cited_card_ids: list[str]
    llm_confidence: str | None  # "high" | "medium" | "low"

    # Output (final)
    citations: list[dict]  # Resolved citation objects with card metadata
    retrieval_cards_considered: int
    retrieval_cards_selected: int

    # Gate metadata
    token_usage: dict | None
    review_required: bool
    review_status: str


# ── Structured LLM output schema (Pydantic — for with_structured_output) ──


class SynthesisOutput(BaseModel):
    """Structured answer from grounded Q&A. Uses json_schema mode (no tool conflicts)."""

    answer: str = Field(
        description="Answer to the user's question based only on the provided cards."
    )
    cited_card_ids: list[str] = Field(
        description="Card IDs from the provided context that support this answer."
    )
    confidence: str = Field(
        description="Self-assessed grounding confidence: high/medium/low"
    )


# ── Input/Output models for the capability (defined here to avoid circular imports with catalog.py) ──


class AskDomainInput(BaseModel):
    """Input for ask.domain grounded Q&A gate."""

    model_config = {"extra": "forbid"}
    workspace_path: str
    domain_id: str
    question: str = Field(..., min_length=1)
    max_cards: int = Field(default=20, ge=1, le=50)
    provider_override: str | None = None


class Citation(BaseModel):
    """A single citation linking an answer claim to a source card."""

    model_config = {"extra": "forbid"}
    card_id: str
    title: str
    snippet: str
    confidence: int | None = None


class GateMetadata(BaseModel):
    """Metadata about the gate invocation."""

    model_config = {"extra": "forbid"}
    gate_id: str
    tier: str = "L2"
    review_required: bool = True
    review_status: str = "pending"
    provider: str = ""
    model: str = ""


class AskDomainOutput(BaseModel):
    """Output from ask.domain grounded Q&A gate."""

    model_config = {"extra": "forbid"}
    answer: str | None
    citations: list[Citation] = Field(default_factory=list)
    gate: GateMetadata = Field(default_factory=lambda: GateMetadata())
    retrieval: dict = Field(default_factory=dict)
    token_usage: dict | None = None


# ── Node 1: Load all non-archived cards from workspace ──


def load_domain_cards(state: AskDomainState) -> dict:
    """Parse cards from workspace; filter archived cards."""
    from construct.schemas.card import parse_card_markdown
    from construct.storage.workspace import WorkspaceLoader

    loader = WorkspaceLoader(Path(state["workspace_path"]))
    card_paths = loader.iter_cards()

    cards: list[dict[str, Any]] = []
    for card_path in card_paths:
        try:
            markdown = card_path.read_text(encoding="utf-8")
            card, body = parse_card_markdown(markdown, source_path=card_path)
            card_data = card.model_dump()
            card_data["body"] = body
            cards.append(card_data)
        except Exception:
            continue  # Skip unparseable cards

    # Filter out archived cards (lifecycle == "archived")
    active = [c for c in cards if c.get("lifecycle") != "archived"]
    return {"cards": active, "retrieval_cards_considered": len(active)}


# ── Node 2: Filter cards by domain_id ──


def filter_by_domain(state: AskDomainState) -> dict:
    """Keep only cards matching the requested domain."""
    filtered = [
        c
        for c in state["cards"]
        if state["domain_id"] in c.get("domains", [])
    ]
    return {"cards": filtered}


# ── Node 3: Rank cards by keyword overlap with question ──


def rank_by_relevance(state: AskDomainState) -> dict:
    """Score cards by token overlap with question; take top max_cards."""
    # Keyword rank (tranche 1 — no embeddings per PRD §14)
    question_tokens = set(state["question"].lower().split())
    scored: list[tuple[int, dict]] = []
    for card in state["cards"]:
        body = (card.get("title", "") + " " + card.get("body", "")).lower()
        overlap = len(question_tokens & set(body.split()))
        scored.append((overlap, card))

    # Sort by overlap descending, take top max_cards
    scored.sort(key=lambda x: -x[0])
    top_cards = [card for _, card in scored[: state["max_cards"]]]
    return {
        "cards": top_cards,
        "retrieval_cards_selected": len(top_cards),
    }


# ── Node 4: Build context string from selected cards ──


def build_context(state: AskDomainState) -> dict:
    """Format card summaries for LLM prompt."""
    parts = []
    for card in state["cards"]:
        parts.append(
            f"--- Card: {card['id']} ---\n"
            f"Title: {card.get('title', 'Untitled')}\n"
            f"Confidence: {card.get('confidence', 'N/A')}\n"
            f"Content: {card.get('body', '')[:2000]}\n"
        )
    context = "\n".join(parts)

    # Hard truncation: if estimated tokens (>100K), drop lowest-ranked cards
    cards = state["cards"]
    estimated_tokens = len(context) // 4
    while estimated_tokens > 100_000 and len(cards) > 1:
        cards = cards[: max(1, int(len(cards) * 0.75))]
        parts = []
        for card in cards:
            parts.append(
                f"--- Card: {card['id']} ---\n"
                f"Title: {card.get('title', 'Untitled')}\n"
                f"Confidence: {card.get('confidence', 'N/A')}\n"
                f"Content: {card.get('body', '')[:2000]}\n"
            )
        context = "\n".join(parts)
        estimated_tokens = len(context) // 4

    return {"context": context}


# ── Node 5: LLM synthesis with structured output ──


def llm_synthesize(state: AskDomainState) -> dict:
    """LLM node: answer question from card context with structured output.

    Uses ChatAnthropic.with_structured_output(method="json_schema")
    to get validated Pydantic output — no tool-choice conflicts.

    Empty context guard: skips LLM call when no cards are available.
    """
    # Empty context guard — skip LLM call when no relevant cards
    if not state.get("context", "").strip():
        return {
            "synthesised_answer": None,
            "cited_card_ids": [],
            "llm_confidence": None,
            "token_usage": None,
            "review_required": False,
            "review_status": "not_required",
        }

    llm = ChatAnthropic(
        model=state.get("model", "claude-sonnet-4-20250514"),
        temperature=0.2,
        max_tokens=4096,
    )
    structured_llm = llm.with_structured_output(SynthesisOutput, method="json_schema")

    messages = [
        SystemMessage(
            content=(
                "You are a knowledge synthesis assistant. Answer the user's question "
                "using ONLY the provided card context. Cite specific card IDs for each claim. "
                "If the context doesn't answer the question, say so clearly."
            )
        ),
        HumanMessage(
            content=f"Question: {state['question']}\n\nContext:\n{state['context']}"
        ),
    ]

    try:
        result: SynthesisOutput = structured_llm.invoke(messages)
        return {
            "synthesised_answer": result.answer,
            "cited_card_ids": result.cited_card_ids,
            "llm_confidence": result.confidence,
        }
    except Exception as exc:
        # Fail loud with structured error; no silent fallback
        return {
            "synthesised_answer": None,
            "cited_card_ids": [],
            "llm_confidence": None,
            "token_usage": {"error": str(exc)},
        }


# ── Node 6: Resolve citations with card metadata ──


def extract_citations(state: AskDomainState) -> dict:
    """Map cited card IDs to citation objects with full metadata.

    Validates every cited ID exists in the retrieved card set.
    Missing IDs produce a warning instead of silent drop.
    """
    card_map = {c["id"]: c for c in state["cards"]}
    citations_list = []
    missing = []

    for cid in state.get("cited_card_ids", []):
        if cid in card_map:
            card = card_map[cid]
            citations_list.append(
                {
                    "card_id": cid,
                    "title": card.get("title", "Untitled"),
                    "snippet": card.get("body", "")[:300],
                    "confidence": card.get("confidence", None),
                }
            )
        else:
            missing.append(cid)

    # Log missing citations — they won't surface to user
    if missing:
        print(f"WARNING: cited card IDs not in retrieved set: {missing}")

    return {
        "citations": citations_list,
        "review_required": True,
        "review_status": "pending",
    }


# ── Graph builder (factory function) ──


def build_ask_domain_graph() -> StateGraph:
    """Construct the compiled LangGraph for ask.domain."""
    builder = StateGraph(AskDomainState)

    builder.add_node("load_domain_cards", load_domain_cards)
    builder.add_node("filter_by_domain", filter_by_domain)
    builder.add_node("rank_by_relevance", rank_by_relevance)
    builder.add_node("build_context", build_context)
    builder.add_node("llm_synthesize", llm_synthesize)
    builder.add_node("extract_citations", extract_citations)

    # Linear topology — no conditional edges in tranche 1
    builder.add_edge(START, "load_domain_cards")
    builder.add_edge("load_domain_cards", "filter_by_domain")
    builder.add_edge("filter_by_domain", "rank_by_relevance")
    builder.add_edge("rank_by_relevance", "build_context")
    builder.add_edge("build_context", "llm_synthesize")
    builder.add_edge("llm_synthesize", "extract_citations")
    builder.add_edge("extract_citations", END)

    return builder.compile()


# ── Exact-match cache ──

_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _cache_key(domain_id: str, question: str) -> str:
    return f"{domain_id}::{question}"


def _cache_fresh(entry: dict) -> bool:
    return (time.time() - entry.get("timestamp", 0)) < _CACHE_TTL_SECONDS


# ── Gate runner ──


def run_gate(
    gate_id: str,
    input_data: AskDomainInput,
    *,
    config_path: Path | None = None,
) -> AskDomainOutput:
    """Run the ask.domain LangGraph gate with provider config resolution.

    Args:
        gate_id: Capability gate identifier (e.g. "ask.domain").
        input_data: Validated AskDomainInput with question, domain, workspace path.
        config_path: Optional override for LLM config YAML path.

    Returns:
        AskDomainOutput with answer, citations, gate metadata, and retrieval info.
    """
    from construct.llm.config import load_llm_config

    # Check cache first
    ck = _cache_key(input_data.domain_id, input_data.question)
    cached = _CACHE.get(ck)
    if cached and _cache_fresh(cached):
        return cached["result"]

    # Load provider config
    config = load_llm_config(config_path)
    gate_cfg = config.gates.get(gate_id, config.gates.get("ask.domain"))
    provider_key = input_data.provider_override or getattr(gate_cfg, "provider", "anthropic")
    provider_cfg = config.providers.get(provider_key, config.providers["anthropic"])

    model = provider_cfg.model

    # Build and invoke graph
    graph = build_ask_domain_graph()
    initial_state: AskDomainState = {
        "question": input_data.question,
        "domain_id": input_data.domain_id,
        "workspace_path": input_data.workspace_path,
        "max_cards": input_data.max_cards,
        "cards": [],
        "context": "",
        "provider": provider_key,
        "model": model,
        "synthesised_answer": None,
        "cited_card_ids": [],
        "llm_confidence": None,
        "citations": [],
        "retrieval_cards_considered": 0,
        "retrieval_cards_selected": 0,
        "token_usage": None,
        "review_required": False,
        "review_status": "not_required",
    }

    result = graph.invoke(initial_state)

    # Build structured output
    output = AskDomainOutput(
        answer=result.get("synthesised_answer"),
        citations=[Citation(**cit) for cit in result.get("citations", [])],
        gate=GateMetadata(
            gate_id=gate_id,
            provider=provider_key,
            model=model,
            review_required=result.get("review_required", False),
            review_status=result.get("review_status", "not_required"),
        ),
        retrieval={
            "cards_considered": result.get("retrieval_cards_considered", 0),
            "cards_selected": result.get("retrieval_cards_selected", 0),
        },
        token_usage=result.get("token_usage"),
    )

    # Store in cache
    _CACHE[ck] = {"result": output, "timestamp": time.time()}

    return output
