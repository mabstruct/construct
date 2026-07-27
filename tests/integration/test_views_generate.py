"""Integration tests for the schema-validated views data generator (D-02/D-04).

The done-bar is ``generate()`` returning ``success=True`` with zero validation
errors against a real install root — proven against BOTH a freshly scaffolded
root (zero cards) and a populated one (cards with connections), because a fresh
root never instantiates ``CardRecord.connections`` and would let the connections
defect pass unnoticed (RESEARCH Pitfall 1).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pydantic
import pytest

from construct.services.knowledge import create_card
from construct.views import models as views_models
from construct.views.contracts import (
    GLOBAL_FILE_CONTRACTS,
    PER_WORKSPACE_FILE_CONTRACTS,
)
from construct.views.generate import generate
from construct.views.lib import frontmatter, parse_cards
from construct.views.models import CardRecord, unwrap_payload

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# The populated-workspace source. ``multi-domain-medium`` was chosen over
# ``single-domain-small`` because both of its workspaces ship a non-empty
# ``connections.json`` whose endpoints are real card ids, so denormalisation
# produces non-empty ``connects_to`` lists and the CardRecord.connections
# contract is genuinely exercised. No connected cards had to be added.
POPULATED_FIXTURE = FIXTURES_DIR / "v02" / "multi-domain-medium"

# D-19's cardinality expression is ``4 + 6·N_workspaces + 1``. An expression
# checked at a single N is indistinguishable from a constant fitted to that N, so
# the round-trip guard runs against a one-workspace root and a two-workspace root
# and the same expression has to hold for both.
ONE_WORKSPACE_FIXTURE = FIXTURES_DIR / "v02" / "single-domain-small"
TWO_WORKSPACE_FIXTURE = POPULATED_FIXTURE

# Every model declared in construct.views.models (D-02 strictness guard).
ALL_MODEL_NAMES = [
    "ViewsEnvelope",
    "BridgeRecord",
    "BridgeSummary",
    "BridgesFile",
    "DomainRecord",
    "DomainsFile",
    "ArticleRecord",
    "ArticlesFile",
    "StatsFile",
    "CardRecord",
    "CardsFile",
    "ConnectionRecord",
    "ConnectionsFile",
    "DigestRecord",
    "DigestsFile",
    "EventRecord",
    "EventsFile",
    # D-18: the two files that had no contract model at all.
    "WorkspaceStatsFile",
    "CurationHistoryFile",
    "CurationCycleRecord",
    "GlobalStatsTotals",
    "WorkspaceStatsTotals",
]


def _populated_install_root(
    tmp_path: Path, fixture: Path = POPULATED_FIXTURE, *, name: str = "populated"
) -> Path:
    """Copy a populated fixture into *tmp_path* and clear its build dir.

    The fixture is shared and generation writes files, so it is never generated
    into in place. The pre-built ``views/build/`` is removed so the fingerprint
    cache cannot short-circuit generation and mask the model change (Pitfall 2).

    *fixture* defaults to the two-workspace root every existing caller uses; the
    round-trip guard passes the one-workspace root as well so D-19's cardinality
    expression is proven at two values of N rather than fitted to one.
    """
    root = tmp_path / name
    shutil.copytree(fixture, root)
    shutil.rmtree(root / "views" / "build", ignore_errors=True)
    return root


def _data_dir(root: Path) -> Path:
    return root / "views" / "build" / "data"


def _payload(path: Path) -> dict:
    return unwrap_payload(json.loads(path.read_text(encoding="utf-8")))


def _expected_slots(data_dir: Path) -> set[str]:
    """The slot names the shared contract tables enumerate for this build.

    Derived from ``views.contracts`` rather than hand-listed, so a file dropped
    from the tables changes this expectation and the set-equality assertions
    below fail instead of quietly checking one file fewer (WR-01).
    """
    ws_ids = sorted(d.name for d in data_dir.iterdir() if d.is_dir())
    slots = set(GLOBAL_FILE_CONTRACTS)
    for ws_id in ws_ids:
        slots |= {f"{ws_id}/{name}" for name in PER_WORKSPACE_FILE_CONTRACTS}
    return slots


def _validate_slots(install_root: Path) -> tuple[set[str], set[str], set[str], int]:
    """Run ``views validate`` and return (passing, failing, missing, exit_code)."""
    from typer.testing import CliRunner

    from construct.cli import app

    result = CliRunner().invoke(
        app, ["views", "validate", "--install-root", str(install_root)]
    )

    def _marked(marker: str) -> set[str]:
        return {
            line.strip().removeprefix(marker).strip().removesuffix("(missing)").strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith(marker)
        }

    return _marked("✓"), _marked("✗"), _marked("?"), result.exit_code


# ---------------------------------------------------------------------------
# The shared contract table (Plan 18-05 Task 1)
# ---------------------------------------------------------------------------


def test_contract_tables_are_the_single_file_enumeration() -> None:
    """``views/contracts.py`` replaces two independent file→model maps.

    Before this plan the same mapping existed twice — ``generate.py``'s adapter
    tables and ``cli.py``'s hand-enumerated list inside ``views validate`` — so
    the writer and the validator could (and did) disagree about which files
    exist. Both now read one table, and the adapter callable is gone: after the
    models were conformed to the writer in Plan 04 the adapter was the identity
    function, and reintroducing one is how the fork happened in the first place.
    """
    import construct.views.generate as gen_mod

    assert len(GLOBAL_FILE_CONTRACTS) == 4, GLOBAL_FILE_CONTRACTS
    assert len(PER_WORKSPACE_FILE_CONTRACTS) == 6, PER_WORKSPACE_FILE_CONTRACTS

    for removed in ("_FILE_MODEL_MAP", "_PER_WS_FILES", "_Adapter", "_as_written"):
        assert not hasattr(gen_mod, removed), (
            f"generate.py still defines {removed}; the adapter tables are the "
            f"second copy of the file→model map this plan deletes"
        )

    # The global and per-workspace ``stats.json`` are different files with
    # different writers and different contracts. One table cannot express that,
    # which is why there are two.
    assert GLOBAL_FILE_CONTRACTS["stats.json"] is not PER_WORKSPACE_FILE_CONTRACTS["stats.json"]


def test_every_written_data_file_is_gated_by_a_contract(tmp_path: Path) -> None:
    """No data file reaches disk unvalidated (research Finding V6, OQ-C).

    Files that fell through the old adapter tables to a bare ``return False``
    were written blind. Deleting those tables without replacing the validation
    would have downgraded ``views generate`` from a validating writer to a blind
    one and left the phase depending on ``views validate`` being run separately,
    which no workflow guarantees.
    """
    root = _populated_install_root(tmp_path)
    report = generate(root)
    assert report.validation_errors == [], report.validation_errors

    data_dir = _data_dir(root)
    ungated = []
    for path in sorted(data_dir.rglob("*.json")):
        # ``_build_meta.json`` is build metadata, not view data.
        if path.name.startswith("_"):
            continue
        rel = path.relative_to(data_dir).as_posix()
        if rel in GLOBAL_FILE_CONTRACTS:
            continue
        if any(rel.endswith(f"/{name}") for name in PER_WORKSPACE_FILE_CONTRACTS):
            continue
        ungated.append(rel)

    assert ungated == [], f"data files written with no contract model: {ungated}"


def test_a_model_violating_payload_is_rejected_and_no_build_is_published(
    tmp_path: Path, monkeypatch
) -> None:
    """T-18-21: the writer validates the bytes it is about to write.

    The corruption here is applied to a *parser's own output*, not to the
    validator, so what fails is the real payload against its real model — which
    is the only way to prove the writer stopped validating an adapted projection
    it then discarded.

    Scope note: the sibling data files ARE rewritten by the failing run, because
    the write loop validates and writes file-by-file. What the run must not do is
    *publish*: ``version.json`` is the pointer the SPA polls and
    ``_build_meta.json`` is the fingerprint cache that would latch the failure
    into permanent success, and neither may advance for a build whose files did
    not all land.
    """
    from construct.views.lib import compute_stats

    root = _populated_install_root(tmp_path)
    first = generate(root)
    assert first.validation_errors == [], first.validation_errors

    build_dir = root / "views" / "build"
    data_dir = _data_dir(root)
    untouched = {
        path: path.read_bytes()
        for path in (
            build_dir / "version.json",
            data_dir / "_build_meta.json",
            data_dir / "stats.json",
        )
    }

    # ``GlobalStatsTotals.workspaces`` is required — it is the discriminator that
    # keeps the global stats.json from validating against the per-workspace
    # model — so a totals map without it is a genuine contract violation of the
    # exact dict the write loop would otherwise hand to ``_write_atomic``.
    monkeypatch.setattr(compute_stats, "compute_global", lambda *a, **k: {"totals": {}})

    # Invalidate only the config fingerprint, so the incremental gate re-runs the
    # build (from cached workspace payloads) rather than short-circuiting.
    cfg_dir = root / ".construct"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(
        "views:\n  workspace_landing: dashboard\n", encoding="utf-8"
    )

    second = generate(root)

    assert second.success is False, "a model-violating payload was accepted"
    assert any(err.startswith("stats.json:") for err in second.validation_errors), (
        second.validation_errors
    )

    for path, before in untouched.items():
        assert path.read_bytes() == before, (
            f"{path.name} changed on a run that failed validation — a partial "
            f"build was published"
        )


def test_views_validate_gates_the_two_previously_ungated_workspace_files(
    tmp_path: Path,
) -> None:
    """D-18's models are only gates if the user's own check invokes them.

    ``<ws>/stats.json`` and ``<ws>/curation-history.json`` were the two files
    with no contract model, and they were also the two files ``views validate``
    never looked at. Both sides now read the same table, so the validator's slot
    list grows with it automatically.
    """
    root = _populated_install_root(tmp_path)
    assert generate(root).validation_errors == []

    passing, failing, _missing, exit_code = _validate_slots(root)

    assert failing == set(), failing
    assert exit_code == 0

    ws_ids = sorted(d.name for d in _data_dir(root).iterdir() if d.is_dir())
    assert ws_ids, "the populated fixture produced no workspace directories"
    for ws_id in ws_ids:
        assert {f"{ws_id}/stats.json", f"{ws_id}/curation-history.json"} <= passing, passing


def test_fresh_workspace_generates_clean(scaffolded_install_root: Path) -> None:
    report = generate(scaffolded_install_root)

    assert report.validation_errors == [], report.validation_errors
    assert report.warnings == [], report.warnings
    assert report.success is True, (report.validation_errors, report.warnings)


def test_populated_workspace_generates_clean(tmp_path: Path) -> None:
    root = _populated_install_root(tmp_path)

    report = generate(root)

    assert report.validation_errors == [], report.validation_errors
    assert report.success is True, report.validation_errors


def test_generated_card_connections_are_id_strings(tmp_path: Path) -> None:
    root = _populated_install_root(tmp_path)

    report = generate(root)
    assert report.validation_errors == [], report.validation_errors

    data_dir = root / "views" / "build" / "data"
    cards_files = sorted(data_dir.glob("*/cards.json"))
    assert cards_files, f"no per-workspace cards.json written under {data_dir}"

    all_cards: list[dict] = []
    for path in cards_files:
        payload = unwrap_payload(json.loads(path.read_text(encoding="utf-8")))
        all_cards.extend(payload["cards"])

    assert all_cards, "populated fixture produced zero cards"

    # generate() validates an *adapted projection* of each card but writes the
    # raw parser dict, so the denormalised neighbour list lands on disk under the
    # parser's key ``connects_to``. It is the same value the CardsFile adapter
    # feeds to CardRecord.connections (generate.py:110, :461).
    # Load-bearing precondition: without a non-empty list somewhere, the type
    # assertion below passes vacuously — the Pitfall 1 failure mode.
    assert any(card["connects_to"] for card in all_cards), (
        "no generated card has connections; CardRecord.connects_to is untested"
    )

    for card in all_cards:
        connections = card["connects_to"]
        assert all(isinstance(entry, str) for entry in connections), (
            f"card {card['id']} has non-string connections: {connections}"
        )
        # Probe edge E3: the ordering contract is sorted-by-target-id.
        assert connections == sorted(connections), (
            f"card {card['id']} connections are not sorted: {connections}"
        )
        # D-01: the model now reads the writer's own key, so the raw written
        # record validates whole rather than through a field-renaming projection.
        record = CardRecord.model_validate(card)
        assert record.connects_to == connections


def test_validation_error_run_does_not_latch_into_permanent_success(
    scaffolded_install_root: Path, monkeypatch
) -> None:
    """CR-01: a run with validation errors must not poison the fingerprint cache.

    Steps 8 and 10 used to run unconditionally, so a run that skipped writes
    because of a validation error still advanced ``version.json`` and still saved
    the *current* source fingerprints. The next run then hit the incremental
    short-circuit and returned ``success=True`` with zero files written — forever,
    until a source file was touched or ``_build_meta.json`` was deleted. This test
    fails (second run reports success) if that gating is removed again.
    """
    import construct.views.generate as gen_mod

    real_validate = gen_mod._validate_file_data

    def _reject_stats(rel_path: str, raw_data: dict, errors: list[str]) -> bool:
        if rel_path == "stats.json":
            errors.append("stats.json: injected validation failure")
            return True
        return real_validate(rel_path, raw_data, errors)

    monkeypatch.setattr(gen_mod, "_validate_file_data", _reject_stats)

    build_dir = scaffolded_install_root / "views" / "build"
    data_dir = build_dir / "data"

    first = generate(scaffolded_install_root)
    assert first.success is False, first.validation_errors
    assert first.validation_errors

    # No build state was committed for the rejected build.
    assert not (build_dir / "version.json").exists(), (
        "version.json advertises a build whose files were never written"
    )
    assert not (data_dir / "_build_meta.json").exists(), (
        "the fingerprint cache was saved for a build that failed validation"
    )

    # The failure must still be reported on an unchanged install root.
    second = generate(scaffolded_install_root)
    assert second.success is False, (
        "a failed build latched into permanent success on the next run"
    )
    assert second.validation_errors
    assert second.total_files_written > 0, (
        "the second run short-circuited instead of retrying the failed build"
    )


def test_malformed_cache_is_a_cache_miss_not_a_crash(
    scaffolded_install_root: Path,
) -> None:
    """WR-03: `views/build/data/` is an untrusted boundary on the way back in.

    ``_load_cached_workspace`` guarded only JSONDecodeError/OSError, so any
    structurally wrong but syntactically valid JSON flowed straight into the
    pipeline — a list where a dict was expected raised AttributeError, a card
    missing ``id`` raised KeyError, a non-int ``confidence`` raised TypeError, and
    all three escaped ``generate()``. The function's documented ``None`` contract
    means the right answer is to re-parse from source.
    """
    generate(scaffolded_install_root)  # populate the cache

    data_dir = scaffolded_install_root / "views" / "build" / "data"
    cards_path = data_dir / "demo" / "cards.json"

    for corruption in (
        ["not", "an", "object"],
        {"data": {"cards": {"not": "a list"}}},
        {"data": {"cards": [{"title": "no id key"}]}},
        {"data": {"cards": [{"id": "c1", "confidence": "high"}]}},
    ):
        cards_path.write_text(json.dumps(corruption), encoding="utf-8")
        # Force the incremental gate to reuse the cache for the unchanged workspace
        # by invalidating only the config fingerprint.
        cfg_dir = scaffolded_install_root / ".construct"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.yaml").write_text(
            f"views:\n  workspace_landing: dashboard\n# {corruption}\n", encoding="utf-8"
        )

        report = generate(scaffolded_install_root)

        assert report.success is True, report.validation_errors
        assert report.validation_errors == []


def test_models_ignore_unknown_fields() -> None:
    """D-03 supersedes the D-02 prohibition this test used to assert.

    The views models are a *derived projection*: a parser that starts emitting
    one more key must not invalidate them, nor invalidate the ``views/build/``
    copies already on users' disks. Forbid-extra stays where an unexpected field
    crosses a trust boundary — see ``test_projection_relaxation_is_scoped``.
    """
    for name in ALL_MODEL_NAMES:
        model = getattr(views_models, name)
        assert issubclass(model, pydantic.BaseModel), name
        assert model.model_config.get("extra") == "ignore", (
            f"{name} does not ignore unknown fields (D-03 relaxation)"
        )


def test_projection_relaxation_is_scoped() -> None:
    """D-03 stops at the projection — the canonical emitters keep forbid."""
    from construct.schemas.config import EventRecord as EmitterEventRecord
    from construct.schemas.workspace import ConnectionsFile as CanonicalConnectionsFile

    assert EmitterEventRecord.model_config.get("extra") == "forbid"
    assert CanonicalConnectionsFile.model_config.get("extra") == "forbid"


def test_relaxed_models_still_reject_malformed_records() -> None:
    """Ignore-extra must not have become accept-anything (D-03 risk).

    A model that ignores extras and requires nothing validates literally
    anything, which removes the gate instead of fixing it.
    """
    for model_name, malformed in (
        # missing required id
        ("CardRecord", {"title": "t", "epistemic_type": "claim", "confidence": 3,
                        "source_tier": 2, "lifecycle": "seed"}),
        # required field of the wrong type
        ("ConnectionRecord", {"source": ["a"], "target": "b", "type": "supports"}),
        # global stats without its totals map
        ("StatsFile", {"by_lifecycle": {}}),
        # workspace stats without its graph metrics
        ("WorkspaceStatsFile", {"totals": {}}),
        # a history payload with no cycles key at all
        ("CurationHistoryFile", {}),
    ):
        model = getattr(views_models, model_name)
        with pytest.raises(pydantic.ValidationError):
            model.model_validate(malformed)


def test_views_generate_cli_command_generates_clean(scaffolded_install_root: Path) -> None:
    """`construct views generate` runs the generator and reports success.

    The generate/validate pair is the D-03 holdout: neither routes through the
    capability registry, so this is the only place the CLI path is proven.
    """
    from typer.testing import CliRunner

    from construct.cli import app

    runner = CliRunner()

    result = runner.invoke(
        app, ["views", "generate", "--install-root", str(scaffolded_install_root)]
    )
    assert result.exit_code == 0, result.stdout
    assert "0 validation errors" in result.stdout

    data_dir = scaffolded_install_root / "views" / "build" / "data"
    assert (data_dir / "stats.json").exists()
    assert (data_dir / "demo" / "cards.json").exists()


def test_views_generate_json_flag_emits_parseable_json(
    scaffolded_install_root: Path,
) -> None:
    """`--json` must emit parseable JSON, not crash.

    Regression guard for the builtin-shadowing trap in ``cli.py``: the module
    defines a Typer command named ``list`` (``construct tag list``), which
    shadows the builtin across the whole module. A bare ``list(...)`` in the
    ``--json`` branch therefore resolved to that command and raised
    ``TypeError: ... not 'OptionInfo'``. The plain form never touched it, so
    the existing CLI test passed while ``--json`` was broken.
    """
    from typer.testing import CliRunner

    from construct.cli import app

    result = CliRunner().invoke(
        app,
        ["views", "generate", "--install-root", str(scaffolded_install_root), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    assert result.exception is None, result.exception

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["validation_errors"] == []
    assert isinstance(payload["warnings"], list)


def test_views_validate_accepts_generated_bytes(
    scaffolded_install_root: Path,
) -> None:
    """VFIX-01: ``views validate`` accepts every file ``views generate`` writes.

    This replaces the characterisation test carried from 15-02, which pinned the
    writer/validator divergence: ``generate()`` validated an *adapted projection*
    of each file and then wrote the raw parser dict, while ``views validate``
    applied the same models to those raw bytes with no adapter and rejected
    three of them. D-01 conformed the models to the writer and reduced the
    generator's adapters to identity, so both commands now gate the same object.

    **This assertion is deliberately weak and Plan 05 replaces it.** The
    scaffolded fixture's ``demo`` workspace has no cards, no connections and no
    digests, so most record models are never instantiated and pass vacuously
    (RESEARCH Pitfall 1). The non-vacuous guard belongs with the file-contract
    tables Plan 05 introduces; the populated round-trip above
    (``test_populated_workspace_generates_clean``) is what carries real weight
    until then.
    """
    from typer.testing import CliRunner

    from construct.cli import app

    runner = CliRunner()
    runner.invoke(app, ["views", "generate", "--install-root", str(scaffolded_install_root)])

    validated = runner.invoke(
        app, ["views", "validate", "--install-root", str(scaffolded_install_root)]
    )

    failing = {
        line.strip().removeprefix("✗ ").strip()
        for line in validated.stdout.splitlines()
        if line.strip().startswith("✗")
    }
    assert failing == set(), failing
    assert validated.exit_code == 0, validated.stdout

    # D-18: the two previously ungated files are now among the files this
    # command actually looks at — a model nothing invokes is not a gate.
    checked = {
        line.strip().removeprefix("✓ ").strip()
        for line in validated.stdout.splitlines()
        if line.strip().startswith("✓")
    }
    assert {"demo/stats.json", "demo/curation-history.json"} <= checked, checked


def test_broken_workspace_domains_yaml_warns_under_its_own_workspace(
    scaffolded_install_root: Path,
) -> None:
    """WR-06: a per-workspace YAML parse warning must not be labelled `(root)`.

    ``_read`` derived the label from ``path.parent.name != path.name``, which can
    never be false for a ``.../domains.yaml``, so every warning claimed ``(root)``.
    generate.py then prepended the bogus id to a file label that already carried
    the real one, yielding ``(root)/demo/domains.yaml`` — one warning naming two
    different locations for one file.
    """
    (scaffolded_install_root / "demo" / "domains.yaml").write_text(
        "domains: [unclosed\n", encoding="utf-8"
    )

    report = generate(scaffolded_install_root)

    yaml_warnings = [w for w in report.warnings if "domains.yaml" in w]
    assert yaml_warnings, report.warnings
    for warning in yaml_warnings:
        assert not warning.startswith("(root)/demo/"), warning
        assert warning.startswith("demo/domains.yaml"), warning


def test_views_install_root_default_is_resolved_at_call_time(
    scaffolded_install_root: Path, monkeypatch
) -> None:
    """WR-09: `typer.Option(Path.cwd(), ...)` bound the default at IMPORT time.

    construct.cli is imported long before any command runs (test runners, the MCP
    server importing it for introspection, long-lived hosts), so the default
    silently pointed at whatever directory the process started in. Combined with
    the missing install-root guard this scaffolded a views tree in an unexpected
    place and called it a success.
    """
    from typer.testing import CliRunner

    from construct.cli import app

    monkeypatch.chdir(scaffolded_install_root)
    result = CliRunner().invoke(app, ["views", "generate"])

    assert result.exit_code == 0, result.stdout
    assert (scaffolded_install_root / "views" / "build" / "data" / "stats.json").exists()


def test_unreadable_views_config_is_reported_not_swallowed(
    scaffolded_install_root: Path,
) -> None:
    """WR-11: a bare `except Exception: pass` hid operator config mistakes.

    An operator who set `views.workspace_landing: wiki` and mistyped the YAML got
    `dashboard` silently — nothing in the warnings log, nothing on stdout. The
    sibling reader in refresh.py logs its equivalent failure.
    """
    cfg_dir = scaffolded_install_root / ".construct"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(
        "views:\n  workspace_landing: [unclosed\n", encoding="utf-8"
    )

    report = generate(scaffolded_install_root)

    # A bad config never fails the build...
    assert report.success is True, report.validation_errors
    # ...but it is no longer invisible.
    assert any("config.yaml" in w for w in report.warnings), report.warnings


def _create_demo_card(install_root: Path) -> str:
    """Write one well-formed card into the ``demo`` workspace via the real writer.

    Returns the resolved card id. The writer's own result is asserted here so a
    refusal to write surfaces as *its* error list, not downstream as a confusing
    KeyError or missing-file error in the test that called this helper.
    """
    result = create_card(
        install_root / "demo",
        {
            "title": "Round trip guard card",
            "epistemic_type": "finding",
            "domains": ["demo"],
            "confidence": 3,
            "source_tier": 3,
            "_summary": "A card written by the service writer, read back by the views parser.",
        },
    )
    assert result.success is True, result.errors
    return result.data["id"]


def test_written_card_frontmatter_satisfies_views_parser_contract(
    scaffolded_install_root: Path,
) -> None:
    """The card writer must emit every field the views parser requires (D-01).

    ``schemas/card.py`` declares ``lifecycle`` with a Pydantic default, so
    ``validate_card_write`` passes on a card whose *bytes on disk* never carry the
    key — Pydantic fills the default in memory. ``views/lib/parse_cards.py`` reads
    **raw** frontmatter and lists ``lifecycle`` in ``REQUIRED_FIELDS``, so it drops
    that card. The contract owner is the writer: frontmatter on disk is
    self-describing (adr-0001), and no reader re-derives schema defaults.

    The naive version of this check — validating the written file through
    ``schemas.card.parse_card_markdown`` — is blind by construction: the Pydantic
    path fills exactly the default the raw path cannot see, so it would report
    success on the very bytes that ``views generate`` throws away. This test
    therefore uses the parser's own splitter, and derives its expectation from
    ``parse_cards.REQUIRED_FIELDS`` at call time rather than hardcoding a field
    name, so a *future* required field the writer omits fails here immediately.
    """
    card_id = _create_demo_card(scaffolded_install_root)
    card_path = scaffolded_install_root / "demo" / "cards" / f"{card_id}.md"
    assert card_path.exists(), f"writer reported success but {card_path} does not exist"

    # The parser's own splitter, NOT schemas.card.parse_card_markdown — see docstring.
    meta, _body = frontmatter.parse(card_path.read_text(encoding="utf-8"))

    # Non-vacuity floors: without these, an empty or unparseable file would
    # trivially satisfy the subset check below.
    assert isinstance(meta, dict) and meta, (
        f"{card_path} parsed to empty frontmatter; the subset check below would pass vacuously"
    )
    assert parse_cards.REQUIRED_FIELDS, (
        "parse_cards.REQUIRED_FIELDS is empty; the subset check below would pass vacuously"
    )

    # Anti-weakening pin: the parser is the locked contract owner's counterparty
    # (D-01). Deleting `lifecycle` from REQUIRED_FIELDS is NOT an allowed way to
    # make this suite green — the writer is the side that must change.
    assert "lifecycle" in parse_cards.REQUIRED_FIELDS, (
        "'lifecycle' was removed from parse_cards.REQUIRED_FIELDS. D-01 locks the "
        "contract on the writer, not the parser; restore the field and fix the writer."
    )

    missing = parse_cards.REQUIRED_FIELDS - set(meta.keys())
    assert not missing, (
        f"{card_path} is missing parser-required frontmatter field(s) {sorted(missing)}; "
        f"views generate will silently drop this card"
    )

    # Named regression pin for the specific field this guard was written for, so a
    # regression reports the symptom by name alongside the derived check above.
    assert meta["lifecycle"] == "seed", (
        f"{card_path} carries lifecycle={meta['lifecycle']!r}, expected the schema default 'seed'"
    )


def test_written_card_reaches_generated_cards_json(
    scaffolded_install_root: Path,
) -> None:
    """A freshly written card must appear in the generated per-workspace cards.json.

    This is the end-to-end symptom the v0.4.1 milestone audit reproduced:
    ``views generate`` reported ``0 validation errors`` and exited 0 while writing
    ``{"cards": []}``, because the parser dropped the card over missing raw
    ``lifecycle``. The naive check — asserting only ``report.validation_errors ==
    []`` — is blind here, because the drop is an advisory *warning* and the run is
    a success by design (D-03). Membership in ``cards.json`` is the only assertion
    that sees it.

    ``generate()`` is called exactly once: a second call can be served by the
    incremental fingerprint cache and would not re-exercise the parser.
    """
    card_id = _create_demo_card(scaffolded_install_root)

    report = generate(scaffolded_install_root)
    assert report.validation_errors == [], report.validation_errors

    cards_path = scaffolded_install_root / "views" / "build" / "data" / "demo" / "cards.json"
    assert cards_path.exists(), f"generator wrote no {cards_path}"
    payload = unwrap_payload(json.loads(cards_path.read_text(encoding="utf-8")))
    ids = [card["id"] for card in payload["cards"]]

    # Non-vacuity floor, so a fully-empty cards.json fails by naming the real
    # cause rather than as a bare membership error.
    assert ids, f"the generator produced zero cards in {cards_path}"
    assert card_id in ids, f"card {card_id!r} is missing from {cards_path}; got {ids}"

    # The targeted message first, so a regression names the offending file...
    assert not [w for w in report.warnings if f"{card_id}.md" in str(w)], (
        f"generate() warned about {card_id}.md: {report.warnings}"
    )
    # ...then the full clean-run contract a fresh scaffold must satisfy.
    assert report.warnings == [], report.warnings
