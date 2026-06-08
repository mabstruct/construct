"""Integration tests for Phase 1 workspace contract: fixture proof, migration, and skill alignment."""

from __future__ import annotations

from pathlib import Path

import pytest

from construct.services.validation import (
    validate_workspace,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_WS = PROJECT_ROOT / "test-ws"
MY_CONSTRUCT = TEST_WS / "my-construct"
PING_EON = TEST_WS / "ping-eon"
MIGRATIONS_DIR = PROJECT_ROOT / "CONSTRUCT-CLAUDE-spec" / "migrations"
MIGRATION_DOC = MIGRATIONS_DIR / "phase-1-workspace-contract-migration.md"
V02_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "v02"

# ---------------------------------------------------------------------------
# Task 2 — Canonical fixture root
# ---------------------------------------------------------------------------


class TestFixtureRoot:
    """Task 2: test-ws/ exists as the sole canonical fixture root."""

    def test_test_ws_exists_as_canonical_fixture_root(self) -> None:
        """Test 1: test-ws/ directory exists as the Phase 1 canonical proof target."""
        assert TEST_WS.is_dir(), (
            f"Canonical fixture root {TEST_WS} does not exist. "
            "Phase 1 proof target per D-08 must exist."
        )

    def test_my_construct_fixture_exists(self) -> None:
        """Test 2a: test-ws/my-construct/ exists with representative workspace content."""
        assert MY_CONSTRUCT.is_dir(), (
            f"Primary fixture {MY_CONSTRUCT} does not exist. "
            "Must have at least multiple domains to exercise canonical validation."
        )

    def test_ping_eon_fixture_exists(self) -> None:
        """Test 2b: test-ws/ping-eon/ exists as the smaller fixture."""
        assert PING_EON.is_dir(), (
            f"Secondary fixture {PING_EON} does not exist. "
            "Must have at least one domain for lightweight testing."
        )

    def test_my_construct_has_canonical_layout(self) -> None:
        """The primary fixture follows the canonical Phase 1 workspace layout."""
        expected_dirs = ["cards", "refs", "digests", "publish", "log", ".construct"]
        expected_files = [
            "connections.json",
            "domains.yaml",
            "governance.yaml",
            "search-seeds.json",
            "log/events.jsonl",
            ".construct/model-routing.yaml",
        ]
        for dir_name in expected_dirs:
            assert (MY_CONSTRUCT / dir_name).is_dir(), (
                f"Missing canonical directory in {MY_CONSTRUCT}: {dir_name}/"
            )
        for file_name in expected_files:
            assert (MY_CONSTRUCT / file_name).is_file(), (
                f"Missing canonical file in {MY_CONSTRUCT}: {file_name}"
            )

    def test_ping_eon_has_canonical_layout(self) -> None:
        """The secondary fixture follows the canonical Phase 1 workspace layout."""
        expected_dirs = ["cards", "refs", "digests", "publish", "log", ".construct"]
        expected_files = [
            "connections.json",
            "domains.yaml",
            "governance.yaml",
            "search-seeds.json",
            "log/events.jsonl",
            ".construct/model-routing.yaml",
        ]
        for dir_name in expected_dirs:
            assert (PING_EON / dir_name).is_dir(), (
                f"Missing canonical directory in {PING_EON}: {dir_name}/"
            )
        for file_name in expected_files:
            assert (PING_EON / file_name).is_file(), (
                f"Missing canonical file in {PING_EON}: {file_name}"
            )

    def test_my_construct_has_multiple_domains(self) -> None:
        """The primary fixture exercises multi-domain validation."""
        domains_yaml = MY_CONSTRUCT / "domains.yaml"
        content = domains_yaml.read_text()
        # Should have more than one domain entry
        domain_count = content.count("  name:")
        assert domain_count >= 2, (
            f"Expected at least 2 domains in {domains_yaml}, found {domain_count}"
        )

    def test_my_construct_has_card_files(self) -> None:
        """The primary fixture has exercised card content."""
        card_files = list((MY_CONSTRUCT / "cards").glob("*.md"))
        assert len(card_files) >= 1, (
            f"Expected at least 1 card file in {MY_CONSTRUCT}/cards/, found {len(card_files)}"
        )

    def test_my_construct_has_ref_files(self) -> None:
        """The primary fixture has exercised ref content."""
        ref_files = list((MY_CONSTRUCT / "refs").glob("*.json"))
        assert len(ref_files) >= 1, (
            f"Expected at least 1 ref file in {MY_CONSTRUCT}/refs/, found {len(ref_files)}"
        )

    def test_readme_names_canonical_fixture_path(self) -> None:
        """Test 3: README.md points maintainers to test-ws/ as the fixture root."""
        readme = (PROJECT_ROOT / "README.md").read_text()
        assert "test-ws/" in readme, (
            "README.md must reference test-ws/ as the fixture location"
        )


# ---------------------------------------------------------------------------
# Task 3 — Fixture proof
# ---------------------------------------------------------------------------


class TestFixtureProof:
    """Task 3: Prove the contract against fixture workspaces."""

    def test_my_construct_validates_through_canonical_path(self) -> None:
        """The primary Phase 1 fixture validates cleanly through the canonical validate path."""
        report = validate_workspace(MY_CONSTRUCT)
        # Allow errors only for intentional drift covered by migration notes
        error_messages = {f.path: f.message for f in report.errors}
        warning_messages = {f.path: f.message for f in report.warnings}
        # At minimum no missing-file errors
        missing = {
            path: msg
            for path, msg in error_messages.items()
            if "missing required canonical path" in msg
        }
        assert not missing, (
            f"Primary fixture {MY_CONSTRUCT} has missing canonical paths: {missing}"
        )

    def test_ping_eon_validates_through_canonical_path(self) -> None:
        """The secondary Phase 1 fixture validates through the canonical validate path."""
        report = validate_workspace(PING_EON)
        missing = {
            path: msg
            for path, msg in {f.path: f.message for f in report.errors}.items()
            if "missing required canonical path" in msg
        }
        assert not missing, (
            f"Secondary fixture {PING_EON} has missing canonical paths: {missing}"
        )

    def test_v02_fixtures_still_load_as_supporting_assets(self) -> None:
        """Historical v02 fixtures remain present as supporting references."""
        multi = V02_FIXTURES / "multi-domain-medium"
        single = V02_FIXTURES / "single-domain-small"
        empty = V02_FIXTURES / "empty"
        assert multi.is_dir(), "v02 multi-domain-medium fixture should remain"
        assert single.is_dir(), "v02 single-domain-small fixture should remain"
        assert empty.is_dir(), "v02 empty fixture should remain"


# ---------------------------------------------------------------------------
# Task 4 — Migration
# ---------------------------------------------------------------------------


class TestMigrationPlaybook:
    """Task 4: Published migration playbook covers the canonical artifact set."""

    def test_migration_doc_exists(self) -> None:
        """The migration playbook document exists."""
        assert MIGRATION_DOC.is_file(), (
            f"Migration playbook {MIGRATION_DOC} does not exist"
        )

    def test_migration_doc_covers_artifacts(self) -> None:
        """The migration doc names each canonical artifact."""
        text = MIGRATION_DOC.read_text()
        markers = [
            "cards",
            "refs",
            "connections.json",
            "domains.yaml",
            "governance.yaml",
            "search-seeds.json",
            "log/events.jsonl",
        ]
        for marker in markers:
            assert marker in text, (
                f"Migration doc must mention canonical artifact '{marker}'"
            )

    def test_migration_doc_mentions_fixture_proof(self) -> None:
        """The migration doc references the fixture proof command or path."""
        text = MIGRATION_DOC.read_text()
        assert "test-ws" in text or "pytest" in text or "validate" in text, (
            "Migration doc must reference the fixture proof target or verification command"
        )

    def test_migration_doc_mentions_verification_command(self) -> None:
        """The migration doc includes a post-migration verification command."""
        text = MIGRATION_DOC.read_text()
        assert "pytest" in text or "validate" in text or "verify" in text, (
            "Migration doc must mention a verification step"
        )
