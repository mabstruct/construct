"""Parse last 100 lines of workspace log/events.jsonl per data-model spec §5.6."""
import json
from pathlib import Path

MAX_EVENTS = 100


def parse(workspace: Path, warnings: list) -> list[dict]:
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
    events = []
    for i, line in enumerate(tail):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError as e:
            warnings.append({"workspace": workspace.name,
                             "file": f"log/events.jsonl line {len(lines) - len(tail) + i + 1}",
                             "reason": f"JSON parse error: {e}"})
            continue
        if isinstance(evt, dict):
            events.append(evt)

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events
