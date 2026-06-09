"""Knowledge artifact operations — card CRUD, connection management, source routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
import re
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
from construct.schemas.config import EventAgent, EventResult
from construct.services.event_log import append_card_event
from construct.services.validation import (
    ArtifactValidationError,
    validate_card_write,
)


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


def _card_dict_to_markdown(card_dict: dict[str, Any]) -> str:
    """Convert a card-data dictionary to canonical markdown with YAML frontmatter."""
    buf = StringIO()
    _yaml.dump(card_dict, buf)
    frontmatter_text = buf.getvalue()

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
) -> OperationResult:
    """Create a new knowledge card in the workspace.

    Steps:
    1. Set defaults for *created* and *author*
    2. Generate a card ID from *title* if not provided
    3. Convert to markdown and validate via *validate_card_write*
    4. Write ``cards/{id}.md``
    5. Log a *create_card* event
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
        markdown = _card_dict_to_markdown(data)
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


