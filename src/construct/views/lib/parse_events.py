"""Read the last 100 lines of a workspace ``log/events.jsonl`` into one shape.

D-17: ``log/events.jsonl`` has had four authors over its life and this reader
used to pass every line through verbatim, so ``events.json`` carried whichever
shape had last written the log. That is the reason ``views validate`` could not
be given a single event contract, and — more seriously — the reason an
audit-derived view could contain records no emitter in this repository could
have produced (T-18-17).

One shape is now canonical: ``construct.schemas.config.EventRecord``'s, the shape
``services/event_log.append_event`` writes today. This module is the only place
that knows any other shape ever existed:

* a canonical line is accepted as written;
* a legacy Claude-native line is migrated into the canonical shape when every
  canonical field can be *derived* from it;
* a line whose canonical fields cannot be derived is dropped and counted into
  the generation-warnings log, never coerced into a fabricated value and never
  silently accepted.

The emitter itself is untouched. It is the canonical author, and conforming it
to a derived projection would be a canonical-write change.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from construct.schemas.config import EventAgent, EventResult

MAX_EVENTS = 100

#: Legacy Claude-native key → canonical key. Sourced from the shapes still
#: present in ``tests/fixtures/v02/*/log/events.jsonl``. Every canonical field
#: is looked up under its own name first, so a canonical line never touches this.
_LEGACY_KEYS: dict[str, str] = {
    "ts": "timestamp",
    "action": "event",
    "agent": "author",
    "target": "card",
    "detail": "details",
}

#: The canonical fields with no default. A line missing any of them, or carrying
#: an underivable value for any of them, is not an event this projection can
#: honestly represent.
_REQUIRED = ("ts", "agent", "action", "result")


def parse(workspace: Path, warnings: list) -> list[dict]:
    """Return the workspace's recent events, canonicalised and newest-first."""
    log_file = workspace / "log" / "events.jsonl"
    if not log_file.is_file():
        return []

    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        warnings.append({"workspace": workspace.name, "file": "log/events.jsonl",
                         "reason": f"read error: {e}"})
        return []

    # Tail
    tail = lines[-MAX_EVENTS:] if len(lines) > MAX_EVENTS else lines
    offset = len(lines) - len(tail)

    # (sort_key, event) pairs. The key is computed here rather than inside the
    # sort so that every surviving event is guaranteed to have a comparable one:
    # sorting on a mix of aware and naive datetimes raises TypeError, and sorting
    # on the raw string orders "09:00+05:30" after "05:00+00:00" even though it
    # is the earlier instant.
    keyed: list[tuple[datetime, dict]] = []

    for i, line in enumerate(tail):
        lineno = offset + i + 1
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            warnings.append({"workspace": workspace.name,
                             "file": f"log/events.jsonl line {lineno}",
                             "reason": f"JSON parse error: {e}"})
            continue
        if not isinstance(raw, dict):
            warnings.append({"workspace": workspace.name,
                             "file": f"log/events.jsonl line {lineno}",
                             "reason": "dropped: line is not a JSON object"})
            continue

        canonical = _canonicalise(raw)
        if canonical is None:
            # The reason names the *fields* that could not be derived, never the
            # line's contents (T-18-20): a dropped line is by definition one this
            # code does not understand, so echoing it would copy arbitrary
            # workspace text — plausibly including secrets — into a build artifact.
            missing = ", ".join(_underivable(raw))
            warnings.append({"workspace": workspace.name,
                             "file": f"log/events.jsonl line {lineno}",
                             "reason": f"dropped: cannot derive canonical event "
                                       f"field(s): {missing}"})
            continue

        keyed.append(canonical)

    # ``list.sort`` is stable and stays stable under ``reverse=True`` — it does
    # not sort-then-reverse — so two events sharing a timestamp keep the order
    # they appear in the file. That tie-break is the whole ordering contract:
    # ``append_event`` stamps whole seconds by default, so same-second events are
    # the common case rather than the edge one.
    keyed.sort(key=lambda pair: pair[0], reverse=True)
    return [event for _, event in keyed]


def _canonicalise(raw: dict) -> tuple[datetime, dict] | None:
    """Return ``(sort_key, canonical_event)``, or ``None`` if not derivable."""
    ts_raw = _pick(raw, "ts")
    agent_raw = _pick(raw, "agent")
    action_raw = _pick(raw, "action")
    result_raw = _pick(raw, "result")

    ts = _parse_ts(ts_raw)
    if ts is None:
        return None

    agent = _enum_value(EventAgent, agent_raw)
    result = _enum_value(EventResult, result_raw)
    if agent is None or result is None:
        return None

    if not isinstance(action_raw, str) or not action_raw.strip():
        return None

    event = {
        # The timestamp is written back exactly as it was read, so microseconds
        # and the original UTC offset reach the SPA byte-for-byte. The parsed
        # value above is used only to order and to validate.
        "ts": ts_raw if isinstance(ts_raw, str) else ts.isoformat(),
        "agent": agent,
        "action": action_raw,
        "target": _optional_text(_pick(raw, "target")),
        "detail": _optional_text(_pick(raw, "detail")),
        "result": result,
    }
    return _sort_key(ts), event


def _underivable(raw: dict) -> list[str]:
    """Which canonical required fields *this* line could not supply."""
    checks = {
        "ts": _parse_ts(_pick(raw, "ts")) is not None,
        "agent": _enum_value(EventAgent, _pick(raw, "agent")) is not None,
        "result": _enum_value(EventResult, _pick(raw, "result")) is not None,
        "action": isinstance(_pick(raw, "action"), str)
        and bool(_pick(raw, "action").strip()),
    }
    return [name for name in _REQUIRED if not checks[name]]


def _pick(raw: dict, canonical_key: str):
    """Read *canonical_key*, falling back to its legacy spelling."""
    if canonical_key in raw:
        return raw[canonical_key]
    legacy = _LEGACY_KEYS.get(canonical_key)
    return raw.get(legacy) if legacy else None


def _parse_ts(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _sort_key(ts: datetime) -> datetime:
    """A comparable, aware timestamp for ordering only.

    A naive value is read as UTC *for the sort key alone* — the stored ``ts``
    keeps whatever it had. Reading it as local time is the one interpretation
    that would be wrong on every machine but the writer's, and refusing to sort
    it at all would mean dropping an otherwise-valid event over a formatting
    detail.
    """
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


def _enum_value(enum_cls, value) -> str | None:
    """Return *value* if it names a member of *enum_cls*, else ``None``.

    Never guesses. An unrecognised agent is exactly the case where a default
    would invent an actor for an audit record.
    """
    if isinstance(value, enum_cls):
        return value.value
    if not isinstance(value, str):
        return None
    try:
        return enum_cls(value).value
    except ValueError:
        return None


def _optional_text(value) -> str | None:
    """Coerce an optional canonical field to ``str | None``.

    Legacy ``details`` is free-form and structured emitters wrote a dict there.
    Serialising it preserves the information the canonical ``str`` field can
    hold, where dropping it would lose an audit detail to a type mismatch.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)
