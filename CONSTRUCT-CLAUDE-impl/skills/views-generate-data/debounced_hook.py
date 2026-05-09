#!/usr/bin/env python3
"""Best-effort trailing-edge debounce for direct per-card views hooks.

This is intentionally simple for the current experimental Claude-native runtime:
- direct `card-create` / `card-connect` calls can schedule one refresh
- multiple calls inside the debounce window collapse to one regeneration
- concurrency hardening is explicitly deferred to future architecture work
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required but not available in this Python interpreter.\n"
        "Run via debounced-hook.sh, which auto-bootstraps a per-skill venv if needed.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: debounced_hook.py <install-root> [source]", file=sys.stderr)
        return 2

    if sys.argv[1] == "--worker":
        if len(sys.argv) != 3:
            print("Usage: debounced_hook.py --worker <install-root>", file=sys.stderr)
            return 2
        return worker(Path(sys.argv[2]).resolve())

    install_root = Path(sys.argv[1]).resolve()
    source = sys.argv[2] if len(sys.argv) > 2 else "direct-card"
    return schedule(install_root, source)


def schedule(install_root: Path, source: str) -> int:
    if not (install_root / "AGENTS.md").is_file():
        print(f"Not a CONSTRUCT installation: missing AGENTS.md at {install_root}", file=sys.stderr)
        return 1

    cfg = load_config(install_root)
    views_cfg = cfg.get("views", {})
    per_card = views_cfg.get("per_card_hooks", {})
    if views_cfg.get("auto_regenerate", True) is False:
        return 0
    if per_card.get("enabled", True) is False:
        return 0
    if per_card.get("mode", "trailing") != "trailing":
        return 0

    build_dir = install_root / "views" / "build"
    if not build_dir.is_dir():
        return 0

    debounce_seconds = parse_debounce_seconds(per_card)
    state_dir = install_root / ".construct" / "state" / "views-hooks"
    state_dir.mkdir(parents=True, exist_ok=True)
    request_path = state_dir / "per-card-request.json"
    pid_path = state_dir / "per-card-worker.pid"
    log_path = state_dir / "per-card-worker.log"

    payload = {
        "requested_at_ms": int(time.time() * 1000),
        "source": source,
        "debounce_seconds": debounce_seconds,
    }
    write_json(request_path, payload)

    live_pid = read_live_pid(pid_path)
    if live_pid is None:
        with log_path.open("ab") as log_file:
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--worker", str(install_root)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")

    if views_cfg.get("confirm_refresh", False):
        print(f"Note: views refresh scheduled ({debounce_seconds}s trailing debounce).")
    return 0


def worker(install_root: Path) -> int:
    state_dir = install_root / ".construct" / "state" / "views-hooks"
    request_path = state_dir / "per-card-request.json"
    pid_path = state_dir / "per-card-worker.pid"
    last_run_path = state_dir / "per-card-last-run.json"
    run_sh = Path(__file__).resolve().parent / "run.sh"

    try:
        while True:
            request = read_json(request_path)
            if request is None:
                return 0
            debounce_seconds = parse_debounce_seconds(request)
            time.sleep(debounce_seconds)
            latest = read_json(request_path)
            if latest is None:
                return 0
            if latest.get("requested_at_ms") != request.get("requested_at_ms"):
                continue

            cfg = load_config(install_root)
            views_cfg = cfg.get("views", {})
            per_card = views_cfg.get("per_card_hooks", {})
            if views_cfg.get("auto_regenerate", True) is False:
                write_json(last_run_path, {
                    "status": "skipped",
                    "reason": "views.auto_regenerate=false",
                    "requested_at_ms": request.get("requested_at_ms"),
                    "finished_at_ms": int(time.time() * 1000),
                })
                return 0
            if per_card.get("enabled", True) is False:
                write_json(last_run_path, {
                    "status": "skipped",
                    "reason": "views.per_card_hooks.enabled=false",
                    "requested_at_ms": request.get("requested_at_ms"),
                    "finished_at_ms": int(time.time() * 1000),
                })
                return 0

            proc = subprocess.run(
                ["bash", str(run_sh), str(install_root)],
                capture_output=True,
                text=True,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            build_id = extract_build_id(output)
            payload = {
                "status": "success" if proc.returncode == 0 else "failed",
                "requested_at_ms": request.get("requested_at_ms"),
                "finished_at_ms": int(time.time() * 1000),
                "source": request.get("source"),
                "build_id": build_id,
                "output": output.strip(),
            }
            write_json(last_run_path, payload)
            return 0 if proc.returncode == 0 else 1
    finally:
        try:
            current = pid_path.read_text(encoding="utf-8").strip()
            if current == str(os.getpid()):
                pid_path.unlink(missing_ok=True)
        except OSError:
            pass


def load_config(install_root: Path) -> dict:
    config_path = install_root / ".construct" / "config.yaml"
    if not config_path.is_file():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def extract_build_id(output: str) -> str | None:
    match = re.search(r"build_id:\s*([0-9a-f]{8})", output)
    return match.group(1) if match else None


def parse_debounce_seconds(payload: dict) -> int:
    raw = payload.get("debounce_seconds", 5)
    if raw is None:
        return 5
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 5


def read_live_pid(pid_path: Path) -> int | None:
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        pid_path.unlink(missing_ok=True)
        return None
    return pid


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    sys.exit(main())