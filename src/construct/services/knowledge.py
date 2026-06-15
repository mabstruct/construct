"""Knowledge artifact operations — card CRUD, connection management, source routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
import re
import shutil
from typing import Any
import json

from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml import YAML

from construct.schemas.card import (
    CardAuthor,
    KnowledgeCard,
    Lifecycle,
    SchemaParseError,
    parse_card_markdown,
)
from construct.schemas.config import (
    DomainRegistryEntry,
    DomainsRegistry,
    EventAgent,
    EventResult,
    ExtractionStatus,
    ReferenceRecord,
    SearchCluster,
    SearchClusterStatus,
    SearchSeedsFile,
)
from construct.schemas.workspace import (
    ConnectionAuthor,
    ConnectionRecord,
    ConnectionType,
    ConnectionsFile,
)
from construct.services.event_log import append_card_event, append_connection_event, append_event
from construct.services.validation import (
    ArtifactValidationError,
    validate_card_write,
    validate_connections_write,
    validate_ref_write,
)
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader


KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


_yaml = YAML()
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4)


@dataclass
class OperationError:
    field: str = "_general"
    reason: str = ""
    suggestion: str = ""


@dataclass
class OperationResult:
    success: bool = True
    message: str = ""
    errors: list[OperationError] = field(default_factory=list)
    data: Any = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_kebab_case(title: str) -> str:
    """Convert an arbitrary title string to a kebab-case ID."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "untitled"


def _resolve_id(workspace_root: Path, desired_id: str) -> str:
    """If *desired_id* already exists as a card, append -2, -3, etc."""
    resolved = desired_id
    counter = 1
    while (workspace_root / "cards" / f"{resolved}.md").exists():
        counter += 1
        resolved = f"{desired_id}-{counter}"
    return resolved


def _card_dict_to_markdown(card_dict: dict[str, Any], body: str | None = None) -> str:
    """Convert a card-data dictionary to canonical markdown with YAML frontmatter.

    When *body* is provided it is used verbatim as the markdown body; otherwise a
    canonical empty section template is emitted.
    """
    buf = StringIO()
    _yaml.dump(card_dict, buf)
    frontmatter_text = buf.getvalue()

    if body is None:
        body = "## Summary\n\n\n\n## Evidence\n\n\n\n## Significance\n\n\n\n## Open Questions\n\n"
    return f"---\n{frontmatter_text}---\n\n{body}"


def _read_card_file(workspace_root: Path, card_id: str) -> tuple[KnowledgeCard, str, dict[str, Any]]:
    """Read and parse a card file, returning (card, body, raw_frontmatter_dict)."""
    card_path = workspace_root / "cards" / f"{card_id}.md"
    if not card_path.exists():
        raise FileNotFoundError(f"Card not found: cards/{card_id}.md")
    try:
        markdown = card_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Could not read cards/{card_id}.md: {exc}") from exc
    # Parse both the validated card and raw dict for field-level editing
    card, body = parse_card_markdown(markdown, source_path=card_path)
    # Re-parse frontmatter as a raw dict for reconstruction
    raw_yaml = YAML(typ="safe")
    parts = markdown.split("\n---\n", 1)
    raw = raw_yaml.load(parts[0][4:]) or {}
    return card, body, raw


# ---------------------------------------------------------------------------
# Card CRUD
# ---------------------------------------------------------------------------


def create_card(
    workspace_root: str | Path,
    card_data: dict[str, Any],
    author: CardAuthor = CardAuthor.construct,
    body: str | None = None,
) -> OperationResult:
    """Create a new knowledge card in the workspace.

    Steps:
    1. Set defaults for *created* and *author*
    2. Generate a card ID from *title* if not provided
    3. Convert to markdown and validate via *validate_card_write*
    4. Write ``cards/{id}.md``
    5. Log a *create_card* event

    *body* is the markdown body placed after the frontmatter; when omitted a
    canonical empty section template is used.
    """
    root = Path(workspace_root)
    data = dict(card_data)

    # Set defaults
    data.setdefault("created", date.today().isoformat())
    if "author" not in data:
        data["author"] = author.value

    # Generate ID from title if not provided
    if "id" not in data or not data["id"]:
        if "title" not in data:
            return OperationResult(
                success=False,
                message="Card must have a title to generate an ID",
                errors=[OperationError(field="title", reason="title is required when id is not provided")],
            )
        data["id"] = _to_kebab_case(str(data["title"]))
    else:
        data["id"] = _to_kebab_case(str(data["id"]))

    # Deduplicate ID
    card_id = _resolve_id(root, data["id"])
    data["id"] = card_id

    # Convert to markdown and validate
    try:
        markdown = _card_dict_to_markdown(data, body=body)
        validate_card_write(markdown)
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        reason = str(exc)
        # Try to determine which field failed
        field = "_general"
        for known_field in ("confidence", "source_tier", "domains", "id", "epistemic_type", "title"):
            if known_field in reason.lower():
                field = known_field
                break
        return OperationResult(
            success=False,
            message=f"Card validation failed: {reason}",
            errors=[OperationError(field=field, reason=reason, suggestion="Check the card fields and try again.")],
        )

    # Ensure cards/ directory exists
    (root / "cards").mkdir(parents=True, exist_ok=True)

    # Write card file
    card_path = root / "cards" / f"{card_id}.md"
    try:
        card_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write card file: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check filesystem permissions and disk space.")],
        )

    # Log event
    epistemic_type = data.get("epistemic_type", "unknown")
    append_card_event(root, EventAgent.construct, "create_card", card_id, f"created {epistemic_type} card")

    return OperationResult(
        success=True,
        message=f"Card '{data.get('title', card_id)}' created as {card_id}",
        data={"id": card_id, "path": f"cards/{card_id}.md"},
    )


def edit_card(
    workspace_root: str | Path,
    card_id: str,
    updates: dict[str, Any],
    author: CardAuthor = CardAuthor.curator,
) -> OperationResult:
    """Update one or more fields of an existing card.

    Reads the current card, applies *updates* at the field level, validates,
    and writes the result back.  Fields not mentioned in *updates* are preserved.
    """
    root = Path(workspace_root)

    # Read existing card
    try:
        _, _, raw = _read_card_file(root, card_id)
    except FileNotFoundError as exc:
        return OperationResult(success=False, message=str(exc), errors=[OperationError(reason=str(exc))])
    except (SchemaParseError, PydanticValidationError, ValueError, OSError) as exc:
        return OperationResult(
            success=False,
            message=f"Could not parse existing card: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="The card file may be corrupt.")],
        )

    # Apply updates (field-level — do not wipe unmentioned fields)
    raw.update(updates)

    # Validate updated card
    try:
        markdown = _card_dict_to_markdown(raw)
        validate_card_write(markdown)
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        reason = str(exc)
        field = "_general"
        for known_field in ("confidence", "source_tier", "domains", "id", "epistemic_type", "title", "lifecycle"):
            if known_field in reason.lower():
                field = known_field
                break
        return OperationResult(
            success=False,
            message=f"Card update validation failed: {reason}",
            errors=[OperationError(field=field, reason=reason, suggestion="Check the updated fields and try again.")],
        )

    # Write updated card
    try:
        (root / "cards" / f"{card_id}.md").write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write updated card: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check filesystem permissions.")],
        )

    # Log event
    updated_fields = list(updates.keys())
    append_card_event(
        root,
        EventAgent.construct,
        "edit_card",
        card_id,
        f"updated fields: {updated_fields}",
    )

    return OperationResult(success=True, message=f"Card '{card_id}' updated", data={"id": card_id})


def archive_card(
    workspace_root: str | Path,
    card_id: str,
    author: CardAuthor = CardAuthor.curator,
) -> OperationResult:
    """Set a card's lifecycle to *archived* while preserving its connections.

    Per D-06 archive preserves connections — ``connects_to`` is kept intact.
    """
    root = Path(workspace_root)

    # Read existing card
    try:
        _, _, raw = _read_card_file(root, card_id)
    except FileNotFoundError as exc:
        return OperationResult(success=False, message=str(exc), errors=[OperationError(reason=str(exc))])
    except (SchemaParseError, PydanticValidationError, ValueError, OSError) as exc:
        return OperationResult(
            success=False,
            message=f"Could not parse existing card: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="The card file may be corrupt.")],
        )

    # Set lifecycle to archived — preserves connects_to
    raw["lifecycle"] = Lifecycle.archived.value

    # Validate
    try:
        markdown = _card_dict_to_markdown(raw)
        validate_card_write(markdown)
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Card archive validation failed: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Write
    try:
        (root / "cards" / f"{card_id}.md").write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write archived card: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Log event
    append_card_event(root, EventAgent.construct, "archive_card", card_id, "lifecycle set to archived")

    return OperationResult(success=True, message=f"Card '{card_id}' archived", data={"id": card_id, "lifecycle": "archived"})


# ---------------------------------------------------------------------------
# Connection CRUD
# ---------------------------------------------------------------------------


def add_connection(
    workspace_root: str | Path,
    from_id: str,
    to_id: str,
    conn_type: ConnectionType,
    note: str | None = None,
    created_by: ConnectionAuthor = ConnectionAuthor.construct,
) -> OperationResult:
    """Add a typed connection between two cards.

    Validates card existence (orphan prevention), duplicate prevention,
    and schema conformance before writing.
    """
    root = Path(workspace_root)

    # Validate kebab-case IDs
    for cid, label in [(from_id, "from_id"), (to_id, "to_id")]:
        if not KEBAB_CASE_PATTERN.fullmatch(cid):
            return OperationResult(
                success=False,
                message=f"Card ID '{cid}' is not valid kebab-case",
                errors=[OperationError(field=label, reason=f"'{cid}' is not kebab-case", suggestion="Use lowercase letters, numbers, and hyphens only.")],
            )

    # Check card files exist (orphan prevention)
    for cid in (from_id, to_id):
        if not (root / "cards" / f"{cid}.md").exists():
            return OperationResult(
                success=False,
                message=f"Card not found: cards/{cid}.md",
                errors=[OperationError(reason=f"Card '{cid}' does not exist", suggestion="Create the card first or check the ID.")],
            )

    # Load existing connections
    loader = WorkspaceLoader(root)
    try:
        connections = loader.load_connections()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Check for duplicate
    for existing in connections.connections:
        if existing.from_ == from_id and existing.to == to_id and existing.type == conn_type:
            return OperationResult(
                success=True,
                message="Connection already exists",
                data={"from": from_id, "to": to_id, "type": conn_type.value},
            )

    # Build new connection record (use alias "from" for Pydantic)
    try:
        new_record = ConnectionRecord(**{  # type: ignore[arg-type]
            "from": from_id,
            "to": to_id,
            "type": conn_type,
            "note": note,
            "created": date.today(),
            "created_by": created_by,
        })
    except (PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Invalid connection record: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check connection parameters.")],
        )

    # Build updated ConnectionsFile
    updated = ConnectionsFile(
        version=connections.version,
        updated=date.today(),
        connection_types=list(ConnectionType),
        connections=[*connections.connections, new_record],
    )

    # Validate
    try:
        validate_connections_write(updated.model_dump(mode="json", by_alias=True))
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Connection validation failed: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Write
    try:
        (root / "connections.json").write_text(
            json.dumps(updated.model_dump(mode="json", by_alias=True), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Log event
    append_connection_event(root, EventAgent.construct, "add_connection", from_id, to_id, conn_type.value)

    return OperationResult(
        success=True,
        message=f"Connection added: {from_id} -> {to_id} ({conn_type.value})",
        data={"from": from_id, "to": to_id, "type": conn_type.value},
    )


def remove_connection(
    workspace_root: str | Path,
    from_id: str,
    to_id: str,
    conn_type: ConnectionType,
) -> OperationResult:
    """Remove a single connection by from + to + type."""
    root = Path(workspace_root)

    loader = WorkspaceLoader(root)
    try:
        connections = loader.load_connections()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Find matching connection
    remaining: list[ConnectionRecord] = []
    found = False
    for existing in connections.connections:
        if existing.from_ == from_id and existing.to == to_id and existing.type == conn_type:
            found = True
        else:
            remaining.append(existing)

    if not found:
        return OperationResult(
            success=False,
            message="Connection not found",
            errors=[OperationError(reason="No matching connection exists")],
        )

    # Build updated ConnectionsFile
    updated = ConnectionsFile(
        version=connections.version,
        updated=date.today(),
        connection_types=list(ConnectionType),
        connections=remaining,
    )

    # Validate
    try:
        validate_connections_write(updated.model_dump(mode="json", by_alias=True))
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Connection validation failed: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Write
    try:
        (root / "connections.json").write_text(
            json.dumps(updated.model_dump(mode="json", by_alias=True), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Log event
    append_connection_event(root, EventAgent.construct, "remove_connection", from_id, to_id, conn_type.value)

    return OperationResult(
        success=True,
        message=f"Connection removed: {from_id} -> {to_id} ({conn_type.value})",
    )


def list_connections(
    workspace_root: str | Path,
    card_id: str | None = None,
    include_archived: bool = False,
) -> OperationResult:
    """List connections from the workspace connections.json.

    Supports optional per-card filtering and archive filtering.
    """
    root = Path(workspace_root)
    loader = WorkspaceLoader(root)

    try:
        connections = loader.load_connections()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load connections.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    result_connections = list(connections.connections)

    # Filter by card
    if card_id is not None:
        result_connections = [
            c for c in result_connections if c.from_ == card_id or c.to == card_id
        ]

    # Filter archived cards
    if not include_archived:
        archived_cards = _get_archived_card_ids(root)
        result_connections = [
            c
            for c in result_connections
            if c.from_ not in archived_cards and c.to not in archived_cards
        ]

    return OperationResult(
        success=True,
        message=f"Found {len(result_connections)} connection(s)",
        data=[c.model_dump(mode="json", by_alias=True) for c in result_connections],
    )


def _get_archived_card_ids(root: Path) -> set[str]:
    """Return the set of card IDs whose lifecycle is *archived*."""
    archived: set[str] = set()
    cards_dir = root / "cards"
    if not cards_dir.exists():
        return archived
    for card_path in cards_dir.glob("*.md"):
        try:
            markdown = card_path.read_text(encoding="utf-8")
            card, _ = parse_card_markdown(markdown, source_path=card_path)
            if card.lifecycle == Lifecycle.archived:
                archived.add(card.id)
        except (SchemaParseError, PydanticValidationError, OSError):
            continue
    return archived


# ---------------------------------------------------------------------------
# Source Routing
# ---------------------------------------------------------------------------


def _suggest_domain(registry: DomainsRegistry, filename: str) -> str | None:
    """Find the first domain whose name, description, or content_categories
    appears as a case-insensitive substring of *filename*.

    Returns the domain ID of the first match, or ``None``.
    """
    filename_lower = filename.lower()
    for domain_id, entry in registry.domains.items():
        # Check domain name
        if entry.name and entry.name.lower() in filename_lower:
            return domain_id
        # Check description
        if entry.description and entry.description.lower() in filename_lower:
            return domain_id
        # Check content categories
        for category in entry.content_categories:
            if category.lower() in filename_lower:
                return domain_id
    return None


def _generate_ref_id(title: str, workspace_root: Path) -> str:
    """Convert *title* to a kebab-case ref ID and deduplicate against
    existing ``refs/*.json`` files.

    If the desired ID already exists, append ``-2``, ``-3``, etc.
    """
    ref_id = _to_kebab_case(title)
    if not ref_id:
        ref_id = "untitled"

    existing = {p.stem for p in workspace_root.glob("refs/*.json")}
    resolved = ref_id
    counter = 1
    while resolved in existing:
        counter += 1
        resolved = f"{ref_id}-{counter}"
    return resolved


def route_source_to_domain(
    workspace_root: str | Path,
    source_path: str | Path,
    domain_hint: str | None = None,
) -> OperationResult:
    """Route a source file from the workspace ``inbox/`` to its target domain.

    Steps:
        1. Verify the source file exists.
        2. Load the domain registry.
        3. Determine the target domain (hint, auto-detect, or fail).
        4. Copy the file to ``{domain}/inbox/raw/{filename}``.
        5. Create and validate a ``ReferenceRecord``.
        6. Write the ref to ``refs/{ref_id}.json``.
        7. Log an ``ingest_paper`` event.
    """
    root = Path(workspace_root).resolve()
    src = Path(source_path)

    # If source_path is relative, resolve it against the workspace root
    if not src.is_absolute():
        src = (root / src).resolve()

    # Verify source file exists
    if not src.is_file():
        return OperationResult(
            success=False,
            message=f"Source file not found: {src}",
            errors=[OperationError(reason=f"No such file: {src}", suggestion="Check the path and try again.")],
        )

    # Load domains registry
    try:
        loader = WorkspaceLoader(root)
        registry = loader.load_domains_registry()
    except WorkspaceLoadError as exc:
        return OperationResult(
            success=False,
            message=f"Could not load domain registry: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Ensure domains.yaml exists and is valid.")],
        )

    # Determine target domain
    filename = src.name
    matched_domain: str | None = None

    if domain_hint is not None:
        # Explicit domain hint — validate it exists
        if domain_hint in registry.domains:
            matched_domain = domain_hint
        else:
            return OperationResult(
                success=False,
                message=f"Domain hint '{domain_hint}' does not exist in domains.yaml",
                errors=[
                    OperationError(
                        field="domain_hint",
                        reason=f"Unknown domain: '{domain_hint}'",
                        suggestion=f"Create the '{domain_hint}' domain first, or use an existing domain: {', '.join(sorted(registry.domains))}",
                    )
                ],
            )
    else:
        # Auto-detect from filename
        matched_domain = _suggest_domain(registry, filename)
        if matched_domain is None:
            return OperationResult(
                success=False,
                message=f"No matching domain found for source '{filename}'",
                errors=[
                    OperationError(
                        reason=f"No domain matched '{filename}'",
                        suggestion="Create a new domain or specify --domain-hint to route to an existing domain.",
                    )
                ],
            )

    # Create target directory
    target_dir = root / matched_domain / "inbox" / "raw"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy source file to target
    target_path = target_dir / filename
    try:
        shutil.copy2(str(src), str(target_path))
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not copy source file: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check filesystem permissions and disk space.")],
        )

    # Generate ref ID and create ReferenceRecord
    source_title = src.stem.replace("-", " ").replace("_", " ").title()
    ref_id = _generate_ref_id(src.stem, root)
    today = date.today()

    try:
        ref = ReferenceRecord(
            id=ref_id,
            title=source_title,
            url=f"inbox://{filename}",
            relevance_score=0.5,
            source_tier=5,
            extraction_status=ExtractionStatus.partial,
            ingested_date=today,
            domain=matched_domain,
            search_cluster="manual-ingest",
        )
    except (PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Invalid reference record: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check reference metadata fields.")],
        )

    # Validate ref write
    try:
        validate_ref_write(ref.model_dump(), relative_path=f"refs/{ref_id}.json")
    except (ArtifactValidationError, PydanticValidationError, ValueError) as exc:
        return OperationResult(
            success=False,
            message=f"Ref validation failed: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Fix the ref metadata and try again.")],
        )

    # Write ref JSON
    ref_path = root / "refs" / f"{ref_id}.json"
    try:
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(
            json.dumps(ref.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write ref file: {exc}",
            errors=[OperationError(reason=str(exc), suggestion="Check filesystem permissions.")],
        )

    # Log event
    append_event(
        root,
        EventAgent.construct,
        "ingest_paper",
        target=ref_id,
        detail=f"routed {filename} to {matched_domain}/inbox/raw/",
    )

    return OperationResult(
        success=True,
        message=f"Source '{filename}' routed to domain '{matched_domain}' as ref '{ref_id}'",
        data={
            "ref_id": ref_id,
            "domain": matched_domain,
            "source_path": str(target_path),
            "ref_path": f"refs/{ref_id}.json",
        },
    )


# ---------------------------------------------------------------------------
# Tag candidate approval pipeline (Phase 6 — SPK-02, SPK-03)
# ---------------------------------------------------------------------------

# D-08: Tags are NEVER auto-accepted. All candidates must pass through the
# curation review cycle. The functions below handle approval, rejection,
# and listing of tag candidates.


def _load_tag_candidates_file(workspace: Path) -> dict:
    """Load log/tag-candidates.json, returning an empty structure if missing."""
    path = workspace / "log" / "tag-candidates.json"
    if not path.is_file():
        return {"candidates": [], "generated_at": "", "total": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("Could not read tag-candidates.json: %s", exc)
        return {"candidates": [], "generated_at": "", "total": 0}


def _write_tag_candidates_file(workspace: Path, payload: dict) -> OperationResult:
    """Write tag-candidates.json atomically."""
    path = workspace / "log" / "tag-candidates.json"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write tag-candidates.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )
    return OperationResult(success=True)


def approve_tag_candidates(
    workspace_root: str | Path,
    candidate_ids: list[str],
) -> OperationResult:
    """Approve tag candidates and write them to search-seeds.json.

    D-08 enforcement: Only explictly approved candidates (passed by ID)
    are written to search-seeds.json. Candidates start as "pending" and
    are never auto-accepted.

    Steps:
      1. Load tag-candidates.json
      2. Filter candidates by ID, skip non-pending
      3. Update matched candidates to "approved"
      4. Load existing search-seeds.json
      5. Add new SearchCluster entries for each approved tag
      6. Write updated tag-candidates.json
      7. Write updated search-seeds.json
      8. Log event
    """
    root = Path(workspace_root)
    data = _load_tag_candidates_file(root)
    candidates = data.get("candidates", [])

    if not candidates:
        return OperationResult(
            success=False,
            message="No tag candidates found in log/tag-candidates.json",
            errors=[OperationError(reason="Empty candidates list")],
        )

    # Build lookup by ID
    candidate_map = {c.get("id", ""): c for c in candidates if "id" in c}
    matched: list[dict] = []
    skipped: list[str] = []

    for cid in candidate_ids:
        c = candidate_map.get(cid)
        if c is None:
            skipped.append(f"{cid}: not found")
        elif c.get("status") != "pending":
            skipped.append(f"{cid}: status is '{c.get('status')}' (not pending)")
        else:
            c["status"] = "approved"
            matched.append(c)

    if not matched:
        return OperationResult(
            success=False,
            message=f"No pending candidates matched the given IDs. Skipped: {', '.join(skipped)}",
            errors=[
                OperationError(
                    reason="No valid pending candidates found",
                    suggestion="Run `construct tag list --status pending` to see available candidates.",
                )
            ],
        )

    # Load existing search-seeds.json
    seeds_path = root / "search-seeds.json"
    existing_seeds: dict = {"version": 1, "updated": None, "clusters": []}
    if seeds_path.is_file():
        try:
            existing_seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger = __import__("logging").getLogger(__name__)
            logger.warning("Could not parse search-seeds.json: %s", exc)

    existing_clusters = existing_seeds.get("clusters", [])
    existing_terms: set[str] = set()
    for cluster in existing_clusters:
        for term in cluster.get("terms", []):
            existing_terms.add(term.lower().strip())

    # Add new clusters for approved tags
    now_iso = datetime.now(timezone.utc).isoformat()
    new_clusters: list[dict] = []
    for c in matched:
        tag = c.get("tag", "").strip()
        if not tag:
            continue
        if tag.lower() in existing_terms:
            continue  # dedup — already seeded

        domain_id = c.get("domain_id") or "general"
        cluster_id = f"tag-{_to_kebab_case(tag)}"

        new_cluster = {
            "id": cluster_id,
            "domain": domain_id,
            "terms": [tag],
            "weight": min(c.get("confidence", 0.5) * 0.8 + 0.2, 1.0),
            "status": SearchClusterStatus.active.value,
            "last_queried": None,
        }
        new_clusters.append(new_cluster)
        existing_terms.add(tag.lower())

    # Update search-seeds.json
    existing_seeds["clusters"] = existing_clusters + new_clusters
    existing_seeds["updated"] = now_iso

    # Write search-seeds.json atomically (T-06-12 mitigation)
    tmp_seeds = seeds_path.with_suffix(".tmp")
    try:
        tmp_seeds.write_text(
            json.dumps(existing_seeds, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_seeds.replace(seeds_path)
    except OSError as exc:
        return OperationResult(
            success=False,
            message=f"Could not write search-seeds.json: {exc}",
            errors=[OperationError(reason=str(exc))],
        )

    # Write updated tag-candidates.json
    data["total"] = len(candidates)
    write_result = _write_tag_candidates_file(root, data)
    if not write_result.success:
        return write_result

    # Log event (T-06-11 — accountability via audit trail)
    append_event(
        root,
        EventAgent.construct,
        "tag_candidates_approved",
        target=",".join(c.get("id", "") for c in matched),
        detail=(
            f"Approved {len(matched)} tag candidate(s), "
            f"added {len(new_clusters)} new search cluster(s) to search-seeds.json"
        ),
    )

    return OperationResult(
        success=True,
        message=(
            f"Approved {len(matched)} tag candidate(s), "
            f"added {len(new_clusters)} search cluster(s). "
            + (f"Skipped: {', '.join(skipped)}" if skipped else "")
        ),
        data={
            "approved_count": len(matched),
            "new_clusters_count": len(new_clusters),
            "skipped": skipped,
        },
    )


def reject_tag_candidates(
    workspace_root: str | Path,
    candidate_ids: list[str],
) -> OperationResult:
    """Reject tag candidates — sets status to "rejected".

    Does NOT update search-seeds.json. Per D-08, candidates stay
    as reviewable artifacts but are marked rejected.

    Steps:
      1. Load tag-candidates.json
      2. Filter candidates by ID, skip non-pending
      3. Update matched candidates to "rejected"
      4. Write updated tag-candidates.json
      5. Log event
    """
    root = Path(workspace_root)
    data = _load_tag_candidates_file(root)
    candidates = data.get("candidates", [])

    if not candidates:
        return OperationResult(
            success=False,
            message="No tag candidates found in log/tag-candidates.json",
        )

    candidate_map = {c.get("id", ""): c for c in candidates if "id" in c}
    matched: list[dict] = []
    skipped: list[str] = []

    for cid in candidate_ids:
        c = candidate_map.get(cid)
        if c is None:
            skipped.append(f"{cid}: not found")
        elif c.get("status") != "pending":
            skipped.append(f"{cid}: status is '{c.get('status')}' (not pending)")
        else:
            c["status"] = "rejected"
            matched.append(c)

    if not matched:
        return OperationResult(
            success=False,
            message="No pending candidates matched the given IDs",
            errors=[OperationError(
                reason="No valid pending candidates to reject",
                suggestion="Run `construct tag list --status pending` to see available candidates.",
            )],
        )

    # Write updated tag-candidates.json
    data["total"] = len(candidates)
    write_result = _write_tag_candidates_file(root, data)
    if not write_result.success:
        return write_result

    # Log event
    append_event(
        root,
        EventAgent.construct,
        "tag_candidates_rejected",
        target=",".join(c.get("id", "") for c in matched),
        detail=f"Rejected {len(matched)} tag candidate(s)",
    )

    return OperationResult(
        success=True,
        message=(
            f"Rejected {len(matched)} tag candidate(s)."
            + (f" Skipped: {', '.join(skipped)}" if skipped else "")
        ),
        data={"rejected_count": len(matched), "skipped": skipped},
    )


def list_tag_candidates(
    workspace_root: str | Path,
    status: str | None = None,
) -> OperationResult:
    """List tag candidates from log/tag-candidates.json.

    Args:
        workspace_root: Path to workspace root.
        status: Optional filter — "pending", "approved", or "rejected".

    Returns:
        OperationResult with candidates list in data.
    """
    root = Path(workspace_root)
    data = _load_tag_candidates_file(root)
    candidates = data.get("candidates", [])

    if status is not None:
        status_filter = status.lower().strip()
        valid_statuses = {"pending", "approved", "rejected"}
        if status_filter not in valid_statuses:
            return OperationResult(
                success=False,
                message=f"Invalid status filter '{status}'. Valid: {', '.join(sorted(valid_statuses))}",
                errors=[OperationError(
                    reason=f"Unknown status: {status}",
                    suggestion="Use --status pending, --status approved, or --status rejected.",
                )],
            )
        candidates = [c for c in candidates if c.get("status") == status_filter]

    # Sort by confidence descending
    candidates = sorted(candidates, key=lambda c: c.get("confidence", 0), reverse=True)

    return OperationResult(
        success=True,
        message=f"Found {len(candidates)} tag candidate(s)",
        data={"candidates": candidates, "total": len(candidates)},
    )


