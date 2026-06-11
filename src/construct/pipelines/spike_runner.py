"""Spike runner — safely run external graph-analysis tools on isolated workspace copies."""
from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SpikeDefinition:
    """Definition of a known spike tool, its command template, and expected outputs."""

    name: str
    description: str
    command_template: str
    expected_output_paths: list[str]
    requires_deps: bool = True


@dataclass
class SpikeResult:
    """Result of a single spike run — captures outputs, timing, and error state."""

    success: bool
    tool_name: str
    started_at: str
    duration_seconds: float
    workspace_path: str
    temp_workspace_path: str
    outputs: dict[str, str] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# Known spike definitions
# ---------------------------------------------------------------------------

KNOWN_SPIKES: dict[str, SpikeDefinition] = {
    "graphify": SpikeDefinition(
        name="graphify",
        description=(
            "Graphify-style ingestion analysis — extract candidate tags "
            "and keywords from refs"
        ),
        command_template="{tool_path} {workspace_copy}",
        expected_output_paths=["candidates.json", "tags.json"],
    ),
    "infranodus": SpikeDefinition(
        name="infranodus",
        description=(
            "InfraNodus-style graph exploration — analyze graph structure "
            "for insight patterns"
        ),
        command_template="{tool_path} --input {workspace_copy}/connections.json",
        expected_output_paths=["report.json"],
    ),
}

# Directories within a workspace that should NOT be copied to the temp workspace.
# These are large derived artifacts safe to regenerate.
_SKIP_DIRS: frozenset[str] = frozenset({"views", "digests", "publish"})

# Default spike timeout in seconds
_DEFAULT_TIMEOUT: int = 300

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_spike(
    tool_name: str,
    workspace: str | Path,
    tool_path: str | None = None,
    install_root: str | Path | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> SpikeResult:
    """Run a governed spike tool on an isolated temp copy of the workspace.

    Creates a temporary workspace copy so canonical data is never at risk.
    Captures stdout, stderr, and expected output files. Results are written
    to ``log/spike-results/{tool_name}-{timestamp}.json`` within the install
    root. The temp directory is always cleaned up (even on failure).

    Args:
        tool_name: Must be a key in :data:`KNOWN_SPIKES`.
        workspace: Path to the CONSTRUCT workspace to copy.
        tool_path: Explicit path to the tool binary. If ``None``, resolves
            *tool_name* via ``shutil.which()``.
        install_root: Where ``log/spike-results/`` lives. Defaults to
            the parent of *workspace*.
        timeout: Max seconds for the subprocess. Default 300 s.

    Returns:
        A :class:`SpikeResult` with captured outputs and error state.
    """
    started_at = datetime.now(timezone.utc).isoformat()

    # Step 1: Validate tool_name against known spikes (T-06-09 mitigation)
    definition = KNOWN_SPIKES.get(tool_name)
    if definition is None:
        return SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=0.0,
            workspace_path=str(workspace),
            temp_workspace_path="",
            error=(
                f"Unknown spike tool: '{tool_name}'. "
                f"Available: {', '.join(sorted(KNOWN_SPIKES))}"
            ),
        )

    root = Path(workspace).resolve()
    if not root.is_dir():
        return SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=0.0,
            workspace_path=str(root),
            temp_workspace_path="",
            error=f"Workspace not found: {root}",
        )

    # Step 2: Resolve tool path
    tool_binary: str | None = tool_path
    if tool_binary is None:
        tool_binary = shutil.which(tool_name)

    if tool_binary is None:
        return SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=0.0,
            workspace_path=str(root),
            temp_workspace_path="",
            error=f"Tool '{tool_name}' not found in PATH. Install it or pass --tool-path.",
        )

    # Step 3: Resolve install root for result storage
    install_root_resolved = Path(install_root).resolve() if install_root else root.parent

    # Step 4: Create temp workspace copy, run tool, capture output
    temp_dir: str | None = None
    start_epoch = datetime.now(timezone.utc)

    try:
        temp_dir = tempfile.mkdtemp(prefix="construct-spike-")
        temp_path = Path(temp_dir)

        _copy_workspace(root, temp_path, definition)

        # Step 5: Format and run command
        # Use shlex.quote() for path arguments and shlex.split() to avoid shell=True
        # per T-06-09 (command injection mitigation — format placeholders, not shell interpolation)
        cmd_str = definition.command_template.format(
            tool_path=shlex.quote(str(tool_binary)),
            workspace_copy=shlex.quote(str(temp_path)),
        )
        cmd_parts = shlex.split(cmd_str)

        logger.info("Running spike '%s': %s", tool_name, cmd_str)

        proc = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout_text = proc.stdout
        stderr_text = proc.stderr
        return_code = proc.returncode
        success = return_code == 0

        # Step 6: Capture expected output files
        outputs = _capture_output(temp_path, definition.expected_output_paths)

        duration = (datetime.now(timezone.utc) - start_epoch).total_seconds()

        result = SpikeResult(
            success=success,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=round(duration, 2),
            workspace_path=str(root),
            temp_workspace_path=str(temp_path),
            outputs=outputs,
            stdout=stdout_text,
            stderr=stderr_text,
        )

        if not success:
            result.error = f"Tool exited with code {return_code}"

    except subprocess.TimeoutExpired:
        duration = (datetime.now(timezone.utc) - start_epoch).total_seconds()
        result = SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=round(duration, 2),
            workspace_path=str(root),
            temp_workspace_path=str(temp_path or ""),
            error=f"Spike timed out after {timeout}s",
        )
    except FileNotFoundError as exc:
        duration = (datetime.now(timezone.utc) - start_epoch).total_seconds()
        result = SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=round(duration, 2),
            workspace_path=str(root),
            temp_workspace_path=str(temp_path or ""),
            error=str(exc),
        )
    except OSError as exc:
        duration = (datetime.now(timezone.utc) - start_epoch).total_seconds()
        result = SpikeResult(
            success=False,
            tool_name=tool_name,
            started_at=started_at,
            duration_seconds=round(duration, 2),
            workspace_path=str(root),
            temp_workspace_path=str(temp_path or ""),
            error=str(exc),
        )
    finally:
        # Step 7: Write results to install_root/log/spike-results/
        _persist_result(install_root_resolved, tool_name, result)

        # Step 8: Always clean up temp dir (T-06-08 mitigation)
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def list_spikes() -> list[dict]:
    """Return a list of known spike definitions as dicts.

    Each entry contains ``name`` and ``description`` for CLI display.
    """
    return [
        {
            "name": sd.name,
            "description": sd.description,
        }
        for sd in sorted(KNOWN_SPIKES.values(), key=lambda s: s.name)
    ]


def register_spike_commands(app: "typer.Typer") -> None:
    """Register ``spike`` CLI command group on a Typer app.

    Adds two subcommands:
        - ``construct spike list`` — show available spike types.
        - ``construct spike run <tool-name>`` — run a spike in isolation.

    Args:
        app: The root Typer application to attach the group to.
    """
    import typer

    spike_app = typer.Typer(
        no_args_is_help=True,
        name="spike",
        help="Run governed spikes on isolated workspace copies.",
    )

    @spike_app.command(name="list")
    def _spike_list() -> None:
        """List available spike types."""
        spikes = list_spikes()
        if not spikes:
            typer.echo("No spike types registered.")
            return
        typer.echo("Available spike types:")
        for s in spikes:
            typer.echo(f"  {s['name']}: {s['description']}")

    @spike_app.command(name="run")
    def _spike_run(
        tool_name: str = typer.Argument(..., help="Spike tool name (e.g. graphify, infranodus)"),
        workspace: Path = typer.Option(
            Path.cwd(), "--workspace", "-w", help="CONSTRUCT workspace path"
        ),
        tool_path: str = typer.Option(
            None, "--tool-path", help="Explicit path to the tool binary"
        ),
        timeout: int = typer.Option(
            _DEFAULT_TIMEOUT, "--timeout", help="Max seconds for spike execution"
        ),
    ) -> None:
        """Run a governed spike on an isolated temp copy of the workspace."""
        result = run_spike(
            tool_name=tool_name,
            workspace=workspace,
            tool_path=tool_path,
            timeout=timeout,
        )
        _display_spike_result(result)

    app.add_typer(spike_app)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _copy_workspace(
    source: Path,
    destination: Path,
    definition: SpikeDefinition,
) -> None:
    """Copy workspace items to *destination* for isolated spike execution.

    Only copies items needed by the spike type. Skips large derived
    directories (``views/``, ``digests/``, ``publish/``) to keep the
    temp copy lean.

    Args:
        source: Resolved workspace root.
        destination: Temp directory path.
        definition: The spike definition controlling what to copy.

    Raises:
        OSError: If any copy operation fails.
    """
    if definition.requires_deps:
        # Always-needed workspace files
        items_to_copy: list[str] = [
            "connections.json",
            "domains.yaml",
        ]

        # Copy individual files
        for item in items_to_copy:
            src = source / item
            if src.exists():
                shutil.copy2(src, destination / item)

        # Copy directory trees (skip derived dirs)
        for dirname in ["cards", "refs"]:
            src_dir = source / dirname
            if src_dir.is_dir():
                dst_dir = destination / dirname
                shutil.copytree(
                    src_dir,
                    dst_dir,
                    ignore=_ignore_derived_dirs,
                )


def _ignore_derived_dirs(current_dir: str, contents: list[str]) -> list[str]:
    """Return items within *contents* that should be skipped during copytree.

    Used as the ``ignore`` callback for :func:`shutil.copytree`. Skips
    any directory whose basename is in ``_SKIP_DIRS``, regardless of depth.
    """
    return [name for name in contents if name in _SKIP_DIRS]


def _capture_output(workspace_copy: Path, expected_paths: list[str]) -> dict[str, str]:
    """Read expected output files from the temp workspace copy.

    Args:
        workspace_copy: Path to the temp workspace copy.
        expected_paths: Relative file paths to capture.

    Returns:
        Dict mapping filename (basename) to file content. Missing files
        are omitted (not included as empty strings).
    """
    outputs: dict[str, str] = {}
    for rel_path in expected_paths:
        file_path = workspace_copy / rel_path
        if file_path.is_file():
            try:
                outputs[file_path.name] = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Could not read spike output %s: %s", file_path, exc)
    return outputs


def _persist_result(
    install_root: Path,
    tool_name: str,
    result: SpikeResult,
) -> None:
    """Write spike result JSON to ``log/spike-results/``.

    Args:
        install_root: The root directory containing ``log/``.
        tool_name: Spike tool name used in the filename.
        result: The result to serialize.
    """
    results_dir = install_root / "log" / "spike-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_path = results_dir / f"{tool_name}-{timestamp}.json"

    serializable = {
        "success": result.success,
        "tool_name": result.tool_name,
        "started_at": result.started_at,
        "duration_seconds": result.duration_seconds,
        "workspace_path": result.workspace_path,
        "temp_workspace_path": result.temp_workspace_path,
        "outputs": result.outputs,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "error": result.error,
    }

    result_path.write_text(
        json.dumps(serializable, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _display_spike_result(result: SpikeResult) -> None:
    """Render a spike result for the CLI user.

    Args:
        result: The spike result to display.
    """
    import typer

    if result.success:
        typer.secho(
            f"✓ Spike '{result.tool_name}' completed in {result.duration_seconds}s",
            fg=typer.colors.GREEN,
        )
    else:
        typer.secho(
            f"✗ Spike '{result.tool_name}' failed: {result.error}",
            fg=typer.colors.RED,
        )

    if result.outputs:
        typer.echo(f"  Captured output files: {', '.join(result.outputs)}")

    if result.stdout:
        # Show first 20 lines of stdout for context
        lines = result.stdout.splitlines()
        if len(lines) > 20:
            typer.echo(f"  stdout ({len(lines)} lines, showing first 20):")
            for line in lines[:20]:
                typer.echo(f"    {line}")
            typer.echo("  ... (output truncated)")
        else:
            typer.echo("  stdout:")
            for line in lines:
                typer.echo(f"    {line}")

    if result.stderr:
        lines = result.stderr.splitlines()
        if len(lines) > 10:
            typer.echo(f"  stderr ({len(lines)} lines, showing first 10):")
            for line in lines[:10]:
                typer.echo(f"    {line}")
        else:
            typer.echo("  stderr:")
            for line in lines:
                typer.echo(f"    {line}")
