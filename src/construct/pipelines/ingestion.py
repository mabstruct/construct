"""Unified ingestion pipeline — files, notes, URLs, and web research."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from construct.schemas.config import EventAgent, EventResult, ExtractionStatus, ReferenceRecord
from construct.schemas.card import CardAuthor
from construct.services.event_log import append_event
from construct.services.knowledge import OperationError, OperationResult, _to_kebab_case, create_card, route_source_to_domain
from construct.services.validation import validate_ref_write
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader


class SourceType:
    FILE = "file"
    URL = "url"
    NOTE = "note"
    RESEARCH = "research"


_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_RESEARCH_PATTERN = re.compile(r"^research:", re.IGNORECASE)


def detect_source_type(source: str) -> str:
    """Detect the type of ingestion source based on its value.

    Per D-04 Specific Ideas:
    - ``.pdf``, ``.txt``, ``.md`` (existing file paths) → *file*
    - ``http://``, ``https://`` → *url*
    - ``research:`` prefix → *research*
    - Everything else → *note*
    """
    if _URL_PATTERN.match(source):
        return SourceType.URL
    if _RESEARCH_PATTERN.match(source):
        return SourceType.RESEARCH
    path = Path(source)
    if path.exists() and path.is_file():
        return SourceType.FILE
    return SourceType.NOTE


def ingest_source(
    workspace_root: str | Path,
    source: str,
    domain_hint: str | None = None,
    author: str = "construct",
) -> OperationResult:
    """Ingest a source into the workspace through the governed ingestion pipeline.

    Per D-04, the flow is:
    capture source → detect type → classify domain → create ref record → generate seed card → log event

    Each step is deterministic and can be re-run.
    """
    root = Path(workspace_root).resolve()
    source_type = detect_source_type(source)

    # Step 1: Load workspace context
    if not root.exists():
        return OperationResult(
            success=False,
            message=f"Workspace not found: {root}",
            errors=[OperationError(reason=f"No such directory: {root}", suggestion="Create the workspace first with `construct init`.")],
        )
    try:
        loader = WorkspaceLoader(root)
        # Ensure workspace is valid by trying to load domains
        _ = loader.load_domains_registry()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load workspace: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Shared variables set by source-type branches
    domain_id: str | None = None
    ref_id: str | None = None
    source_title: str | None = None
    source_detail: str | None = None

    # Step 2: Handle source based on type
    if source_type == SourceType.FILE:
        # Route existing file to domain via knowledge service
        result = route_source_to_domain(root, source, domain_hint)
        if not result.success:
            return result
        ref_id = result.data.get("ref_id", "unknown") if result.data else "unknown"
        source_title = Path(source).stem.replace("-", " ").replace("_", " ").title()
        source_detail = f"file '{Path(source).name}'"
        domain_id = result.data.get("domain") if result.data else None

    elif source_type == SourceType.URL:
        # Create ref record for URL — no file to route
        source_title = source.replace("https://", "").replace("http://", "").split("/")[0].title()
        ref_id = _to_kebab_case(source_title)
        deduped = _deduplicate_ref_id(root, ref_id)
        if deduped[1] is not None:
            return deduped[1]
        ref_id = deduped[0]

        today = date.today()

        # Determine domain
        domain_id = domain_hint or _get_first_domain(root)
        if domain_id is None:
            return OperationResult(
                success=False,
                message="No domain found for URL ingestion. Specify --domain or create a domain first.",
                errors=[OperationError(reason="No domains configured", suggestion="Run `construct init` to create a workspace with a domain.")],
            )

        try:
            ref = ReferenceRecord(
                id=ref_id,
                title=source_title,
                url=source,
                relevance_score=0.5,
                source_tier=5,
                extraction_status=ExtractionStatus.partial,
                ingested_date=today,
                domain=domain_id,
                search_cluster="web-ingest",
            )
            validate_ref_write(ref.model_dump(), relative_path=f"refs/{ref_id}.json")
            _write_ref_file(root, ref_id, ref)
        except (ValueError, OSError) as exc:
            return OperationResult(
                success=False,
                message=f"Could not create ref for URL: {exc}",
                errors=[OperationError(reason=str(exc))],
            )
        source_detail = f"URL '{source}'"

    else:  # NOTE or RESEARCH
        # Create ref record from raw text/note
        note_text = source
        if source_type == SourceType.RESEARCH:
            note_text = source[len("research:"):].strip()
            source_title = "Research: " + note_text[:60]
        else:
            source_title = note_text[:60].strip() if note_text else "Untitled Note"

        ref_id = _to_kebab_case(source_title[:40])
        deduped = _deduplicate_ref_id(root, ref_id)
        if deduped[1] is not None:
            return deduped[1]
        ref_id = deduped[0]

        today = date.today()

        domain_id = domain_hint or _get_first_domain(root)

        try:
            ref = ReferenceRecord(
                id=ref_id,
                title=source_title,
                url=f"note://{ref_id}",
                abstract=note_text,
                relevance_score=0.5,
                source_tier=5,
                extraction_status=ExtractionStatus.partial,
                ingested_date=today,
                domain=domain_id or "_general",
                search_cluster="manual-ingest",
            )
            validate_ref_write(ref.model_dump(), relative_path=f"refs/{ref_id}.json")
            _write_ref_file(root, ref_id, ref)
        except (ValueError, OSError) as exc:
            return OperationResult(
                success=False,
                message=f"Could not create ref for note: {exc}",
                errors=[OperationError(reason=str(exc))],
            )
        source_detail = f"note '{source_title}'"

    # Step 3: Create seed card from the ref
    card_data = {
        "title": source_title or "Untitled",
        "epistemic_type": "finding",
        "domains": [domain_id] if domain_id else [],
        "confidence": 1,
        "source_tier": 5,
        "content_categories": [],
        "author": author,
        "summary": f"Seed card from ingested {source_type}: {source_title}",
    }
    card_result = create_card(str(root), card_data, author=CardAuthor(author))

    # Step 4: Log event
    append_event(
        root, EventAgent.construct,
        "ingest_source",
        target=ref_id or "unknown",
        detail=f"Ingested {source_detail} as ref '{ref_id}' (type: {source_type})",
    )

    if not card_result.success:
        # Ref was created but seed card failed — partial success
        return OperationResult(
            success=True,
            message=f"Source ingested: ref '{ref_id}' created (card creation warning: {card_result.message})",
            data={
                "ref_id": ref_id,
                "source_type": source_type,
                "card_result": card_result.message,
                "card_created": False,
            },
        )

    return OperationResult(
        success=True,
        message=f"Source ingested: ref '{ref_id}' + seed card created",
        data={
            "ref_id": ref_id,
            "source_type": source_type,
            "card_id": card_result.data.get("id") if card_result.data else None,
            "card_created": True,
        },
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deduplicate_ref_id(root: Path, desired_id: str) -> tuple[str, None] | tuple[None, OperationResult]:
    """If *desired_id* already exists as a ref file, append -2, -3, etc."""
    resolved = desired_id
    counter = 1
    while (root / "refs" / f"{resolved}.json").exists():
        counter += 1
        resolved = f"{desired_id}-{counter}"
    return (resolved, None)


def _get_first_domain(root: Path) -> str | None:
    """Return the first domain ID from domains.yaml, or None."""
    try:
        loader = WorkspaceLoader(root)
        registry = loader.load_domains_registry()
        domains = list(registry.domains.keys())
        return domains[0] if domains else None
    except (WorkspaceLoadError, OSError):
        return None


def _write_ref_file(root: Path, ref_id: str, ref: ReferenceRecord) -> None:
    """Write a ref record to refs/{ref_id}.json."""
    ref_path = root / "refs" / f"{ref_id}.json"
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(
        json.dumps(ref.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
