from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from construct.cli import app


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _tree(root: Path) -> list[str]:
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{relative}/" if path.is_dir() else relative)
    return sorted(entries)


def test_construct_init_creates_full_workspace_scaffold(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    expected_tree = sorted(line for line in (FIXTURES_DIR / "expected-workspace-tree.txt").read_text().splitlines() if line)

    result = runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples,notes\npeer-reviewed papers,expert blogs\nexample seed,another seed\n",
    )

    assert result.exit_code == 0, result.stdout
    assert _tree(workspace) == expected_tree
    assert "Initialized CONSTRUCT workspace" in result.stdout
    assert "Domain slug" in result.stdout
    assert "Display name" in result.stdout


def test_init_writes_registry_and_domain_detail_file(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"

    result = runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples,notes\npeer-reviewed papers\nexample seed\n",
    )

    assert result.exit_code == 0, result.stdout
    domains_yaml = (workspace / "domains.yaml").read_text()
    domain_yaml = (workspace / "domains" / "example-domain" / "domain.yaml").read_text()
    assert "domains/example-domain/domain.yaml" in domains_yaml
    assert "id: example-domain" in domain_yaml
    assert "content_categories:" in domain_yaml
    assert "research_seeds:" in domain_yaml


def test_init_normalizes_taxonomy_seeds_to_kebab_case(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"

    result = runner.invoke(
        app,
        ["init", str(workspace)],
        input="physics\nPhysics\nPhysics research\nquantum gravity,string theory,general relativity\npeer-reviewed papers\nquantum gravity\n",
    )

    assert result.exit_code == 0, result.stdout
    domain_yaml = (workspace / "domains" / "physics" / "domain.yaml").read_text()
    assert "- quantum-gravity" in domain_yaml
    assert "- string-theory" in domain_yaml
    assert "- general-relativity" in domain_yaml


def test_init_normalizes_domain_slug_to_kebab_case(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"

    result = runner.invoke(
        app,
        ["init", str(workspace)],
        input="Quantum Gravity\nQuantum Gravity\nPhysics research\nquantum gravity\npeer-reviewed papers\nquantum gravity\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (workspace / "domains" / "quantum-gravity" / "domain.yaml").exists()
    domains_yaml = (workspace / "domains.yaml").read_text()
    assert "quantum-gravity:" in domains_yaml


def test_validate_reports_warnings_without_failing(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples\npeer-reviewed papers\nexample seed\n",
    )
    (workspace / "cards" / "invalid-card-no-summary.md").write_text(
        (FIXTURES_DIR / "invalid" / "invalid-card-no-summary.md").read_text()
    )

    result = runner.invoke(app, ["validate", str(workspace)])

    assert result.exit_code == 0, result.stdout
    assert "WARNING cards/invalid-card-no-summary.md" in result.stdout
    assert "0 error(s), 1 warning(s)" in result.stdout


def test_validate_reports_errors_with_nonzero_exit(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples\npeer-reviewed papers\nexample seed\n",
    )
    (workspace / "domains" / "example-domain" / "domain.yaml").unlink()
    (workspace / "cards" / "broken-card.md").write_text("---\nid: broken-card\ntitle: [broken\n---\n")

    result = runner.invoke(app, ["validate", str(workspace)])

    assert result.exit_code == 1
    assert "ERROR domains/example-domain/domain.yaml" in result.stdout
    assert "ERROR cards/broken-card.md" in result.stdout


def test_status_labels_canonical_and_derived_paths(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    runner.invoke(
        app,
        ["init", str(workspace)],
        input="example-domain\nExample Domain\nExample scope\nexamples\npeer-reviewed papers\nexample seed\n",
    )

    result = runner.invoke(app, ["status", str(workspace)])

    assert result.exit_code == 0
    assert "Canonical: cards [present]" in result.stdout
    assert "Canonical: domains.yaml [present]" in result.stdout
    assert "Derived: db [present]" in result.stdout
    assert "Derived: views [present]" in result.stdout
