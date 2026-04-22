from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
