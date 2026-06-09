"""Event logging service for knowledge operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from construct.schemas.config import EventAgent, EventRecord, EventResult


def append_event(
    workspace_root: str | Path,
    agent: EventAgent,
    action: str,
    *,
    target: str | None = None,
    detail: str | None = None,
    result: EventResult = EventResult.success,
) -> None:
    """Append a JSON line to log/events.jsonl in the given workspace.

    Non-blocking — if the file cannot be written, a warning is printed to
    stderr but no exception is raised.
    """
    record = EventRecord(
        ts=datetime.now(timezone.utc),
        agent=agent,
        action=action,
        target=target,
        detail=detail,
        result=result,
    )
    events_path = Path(workspace_root) / "log" / "events.jsonl"
    try:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
    except OSError as exc:
        print(f"WARNING: could not write event to {events_path}: {exc}", file=sys.stderr)


def append_card_event(
    workspace_root: str | Path,
    agent: EventAgent,
    action: str,
    card_id: str,
    detail: str | None = None,
    result: EventResult = EventResult.success,
) -> None:
    """Convenience wrapper that sets target=card_id."""
    append_event(
        workspace_root,
        agent,
        action,
        target=card_id,
        detail=detail,
        result=result,
    )


def append_connection_event(
    workspace_root: str | Path,
    agent: EventAgent,
    action: str,
    connection_from: str,
    connection_to: str,
    connection_type: str,
    result: EventResult = EventResult.success,
) -> None:
    """Convenience wrapper with detail=f"{connection_from}->{connection_to} ({connection_type})"."""
    detail = f"{connection_from}->{connection_to} ({connection_type})"
    append_event(
        workspace_root,
        agent,
        action,
        target=detail,
        detail=detail,
        result=result,
    )
