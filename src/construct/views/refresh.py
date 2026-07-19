"""Post-workflow views refresh — a side effect, NEVER a success condition (D-12).

``refresh_views`` is the single shared tail-of-workflow hook called by
``curation.run``, ``research.run`` and ``daily.run``. It exists as one helper rather
than three direct generator calls because all three call sites need the same
existence check, the same config gate and the same swallow-and-log semantics;
triplicating that would give the D-12 side-effect rule three independent places
to be broken.

**The contract callers must honour (D-12):** the returned outcome is for *logging*.
No caller may branch on it to set, degrade or fail a workflow status. A refresh that
is skipped, disabled or failed leaves the workflow's reported status exactly as it
would have been had the refresh never run. This mirrors the rule the three skill docs
already state ("always preserve this skill's success status — the hook is a side
effect, not a success condition") and carries it into Python.

The module deliberately imports **nothing** from ``construct.llm``: the dependency
edge runs ``llm → views`` and must stay acyclic. ``_sanitize_error`` is therefore
replicated here rather than imported from ``llm/curation_run.py``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

RefreshStatus = Literal["skipped", "succeeded", "failed"]


@dataclass(frozen=True)
class RefreshOutcome:
    """What the refresh did. Callers LOG this; no caller branches on it (D-12)."""

    status: RefreshStatus
    reason: str = ""
    build_id: str = ""
    files_written: int = 0


def _sanitize_error(exc: Exception) -> str:
    """Reduce an exception to a class name + first safe line (never echo raw text).

    Behaviourally identical to ``construct.llm.curation_run._sanitize_error``, and
    deliberately *replicated* rather than imported: importing it would create a
    ``views → llm`` edge, reversing the only dependency direction this package has
    (T-15-13 / the D-08 sanitisation discipline applies to both copies).
    """
    text = str(exc).strip()
    first = text.splitlines()[0] if text else ""
    return f"{type(exc).__name__}: {first}" if first else type(exc).__name__


def _read_views_config(install_root: Path) -> dict:
    """Read the ``views:`` block from ``<install_root>/.construct/config.yaml``.

    Read defensively: a missing file, an unparseable file or a missing ``views``
    section all resolve to ``{}``, which the callers below treat as "enabled".
    Config is an operator convenience — a malformed one must never be the reason a
    workflow tail raises.

    Note this is the *install-level workspace* config (the same file
    ``generate.py`` reads for ``views.workspace_landing`` and ``fingerprint.py``
    fingerprints), NOT ``construct.llm.config``. ``LlmConfig`` declares
    ``extra="forbid"`` and has no ``views`` section; a ``views:`` key there would be
    a load-time error, and it is the wrong scope besides — these keys are per
    install root, and the LLM config is global.
    """
    cfg_path = install_root / ".construct" / "config.yaml"
    if not cfg_path.is_file():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        views_cfg = data.get("views", {}) if isinstance(data, dict) else {}
        return views_cfg if isinstance(views_cfg, dict) else {}
    except Exception as exc:  # noqa: BLE001 — a bad config never breaks a workflow tail (D-12)
        logger.warning("views refresh: unreadable config at %s: %s", cfg_path, _sanitize_error(exc))
        return {}


def refresh_views(install_root: Path | str) -> RefreshOutcome:
    """Regenerate views data under ``install_root``; never raise, never gate a status.

    Gates, in order:

    1. **Existence.** No ``<install_root>/views/build/`` directory → skipped without
       calling the generator. An install root that has never had views built is not
       opting into having them built by a background workflow tail.
    2. **Config.** ``views.auto_regenerate: false`` → skipped. This is the operator
       kill switch (T-15-12): it bounds the worst case of a sweep running at the tail
       of every workflow on a large install root.

    Otherwise the generator runs and its report is translated: success with no
    validation errors → ``succeeded`` (carrying build id and files-written); anything
    else → ``failed`` with a short reason. A raising generator is caught and also
    becomes ``failed``.

    Returns a :class:`RefreshOutcome` for the caller to LOG. Per D-12 no caller may
    use it to set a workflow status.
    """
    root = Path(install_root)

    # Gate 1 — existence.
    if not (root / "views" / "build").is_dir():
        return RefreshOutcome(status="skipped", reason="no views/build directory at install root")

    # Gate 2 — config.
    views_cfg = _read_views_config(root)
    if views_cfg.get("auto_regenerate") is False:
        return RefreshOutcome(status="skipped", reason="views.auto_regenerate is false")

    # ``views.confirm_refresh`` selects how loudly the refresh reports itself, not
    # whether it runs. The skill docs define it as "on success, append `✓ views
    # updated`; otherwise stay silent (the SPA polls version.json)" — i.e. it is a
    # verbosity switch, never a pre-run human confirmation. These call sites are
    # non-interactive workflow tails with no human present, so there is nobody to
    # confirm *to*; the flag is honoured by surfacing an explicit confirmation in
    # the outcome reason that callers already log, and is deliberately NOT treated
    # as a reason to skip. Skipping on it would mean an operator who asked to be
    # *told about* refreshes silently stopped getting them.
    confirm = bool(views_cfg.get("confirm_refresh"))

    # D-12: the refresh is a side effect. Everything below this line either returns
    # an outcome or is swallowed — no exception escapes into the calling workflow.
    try:
        from construct.views.generate import generate  # local import: keeps llm → views one-way

        report = generate(root)
    except Exception as exc:  # noqa: BLE001 — D-12: a broken refresh must not fail its workflow
        safe = _sanitize_error(exc)
        logger.warning("views refresh failed for %s: %s", root, safe)
        return RefreshOutcome(status="failed", reason=safe)

    if report.success and not report.validation_errors:
        reason = "✓ views updated" if confirm else ""
        return RefreshOutcome(
            status="succeeded",
            reason=reason,
            build_id=report.build_id or "",
            files_written=report.total_files_written,
        )

    reason = f"{len(report.validation_errors)} validation error(s)"
    logger.warning("views refresh reported problems for %s: %s", root, reason)
    return RefreshOutcome(status="failed", reason=reason, build_id=report.build_id or "")
