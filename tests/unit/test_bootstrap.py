from __future__ import annotations

from pathlib import Path
import tomllib

import construct.cli
from construct import __version__


def test_package_exports_version() -> None:
    assert __version__


def test_cli_module_exposes_typer_app_and_entrypoint() -> None:
    assert construct.cli.app is not None
    assert callable(construct.cli.main)


def test_project_script_targets_cli_main() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())

    assert data["project"]["scripts"]["construct"] == "construct.cli:main"
