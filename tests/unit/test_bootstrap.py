from __future__ import annotations

from pathlib import Path
import re
import tomllib

from typer.testing import CliRunner

import construct.cli
from construct import __version__
from construct._release import __version__ as release_version
from construct.versioning import BUILD_STAMP_LEN, build_number, version_string


def test_package_exports_version() -> None:
    assert __version__ == version_string()


def test_version_uses_release_and_build_stamp() -> None:
    assert __version__ == f"{release_version}.{build_number()}"
    assert re.fullmatch(rf"{re.escape(release_version)}\.\d{{{BUILD_STAMP_LEN}}}", __version__)


def test_cli_module_exposes_typer_app_and_entrypoint() -> None:
    assert construct.cli.app is not None
    assert callable(construct.cli.main)


def test_project_script_targets_cli_main() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())

    assert data["project"]["scripts"]["construct"] == "construct.cli:main"


def test_cli_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(construct.cli.app, ["--version"])
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == __version__
    assert re.fullmatch(rf"{re.escape(release_version)}\.\d{{{BUILD_STAMP_LEN}}}", result.stdout.strip())
