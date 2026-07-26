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

from construct.services.knowledge import create_card
from construct.views import models as views_models
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
]


def _populated_install_root(tmp_path: Path) -> Path:
    """Copy the shared populated fixture into *tmp_path* and clear its build dir.

    The fixture is shared and generation writes files, so it is never generated
    into in place. The pre-built ``views/build/`` is removed so the fingerprint
    cache cannot short-circuit generation and mask the model change (Pitfall 2).
    """
    root = tmp_path / "populated"
    shutil.copytree(POPULATED_FIXTURE, root)
    shutil.rmtree(root / "views" / "build", ignore_errors=True)
    return root


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
        "no generated card has connections; CardRecord.connections is untested"
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
        # The value the writer emits must satisfy the model the validator applies.
        record = CardRecord(
            id=card["id"],
            title=card["title"],
            epistemic_type=card["epistemic_type"],
            confidence=card["confidence"],
            source_tier=card["source_tier"],
            lifecycle=card["lifecycle"],
            summary=card.get("summary_excerpt", ""),
            connections=connections,
        )
        assert record.connections == connections


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


def test_models_still_forbid_unknown_fields() -> None:
    for name in ALL_MODEL_NAMES:
        model = getattr(views_models, name)
        assert issubclass(model, pydantic.BaseModel), name
        assert model.model_config.get("extra") == "forbid", (
            f"{name} does not forbid unknown fields (D-02 prohibition)"
        )


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


def test_views_validate_does_not_yet_accept_generated_bytes(
    scaffolded_install_root: Path,
) -> None:
    """Characterisation test for the writer/validator divergence (carried from 15-02).

    ``generate()`` validates an *adapted projection* of each file (generate.py's
    ``_FILE_MODEL_MAP`` / per-file adapters) but writes the **raw parser dict**.
    ``views validate`` applies the same models to the raw bytes with no adapter,
    so three files the generator called clean are rejected on disk.

    This is pre-existing — before this plan nothing wired generation, so
    ``views validate`` had no generator output to disagree with and the conflict
    could not be observed. Resolving it means choosing which shape is canonical
    (widen the models to the written bytes, share the generator's adapter with
    the validator, or write the projection), a contract decision with Phase 16/17
    SPA consequences that is deliberately NOT taken inside Plan 03.

    This test pins the current, honest state. **It must be deleted when the
    divergence is resolved** — it turns red the moment validate starts passing.
    """
    from typer.testing import CliRunner

    from construct.cli import app

    runner = CliRunner()
    runner.invoke(app, ["views", "generate", "--install-root", str(scaffolded_install_root)])

    validated = runner.invoke(
        app, ["views", "validate", "--install-root", str(scaffolded_install_root)]
    )

    assert validated.exit_code == 1, validated.stdout
    # The exact divergent set, so a change in its shape is visible rather than silent.
    failing = {
        line.strip().removeprefix("✗ ").strip()
        for line in validated.stdout.splitlines()
        if line.strip().startswith("✗")
    }
    assert failing == {"stats.json", "demo/connections.json", "demo/events.json"}, failing


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
