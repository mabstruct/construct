"""Workspace validation service with structured errors and warnings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from construct.schemas.card import KnowledgeCard, SchemaParseError, parse_card_markdown, validate_card_markdown
from construct.schemas.config import DomainsRegistry, EventRecord, GovernanceConfig, ReferenceRecord, SearchSeedsFile
from construct.schemas.workspace import ConnectionsFile
from construct.storage.workspace import WorkspaceLoadError, WorkspaceLoader


@dataclass(frozen=True)
class ValidationFinding:
    severity: str
    path: str
    message: str


@dataclass
class ValidationReport:
    errors: list[ValidationFinding] = field(default_factory=list)
    warnings: list[ValidationFinding] = field(default_factory=list)

    @property
    def findings(self) -> list[ValidationFinding]:
        return [*self.errors, *self.warnings]

    @property
    def by_file(self) -> dict[str, list[ValidationFinding]]:
        grouped: dict[str, list[ValidationFinding]] = {}
        for finding in self.findings:
            grouped.setdefault(finding.path, []).append(finding)
        return grouped

    def add_error(self, path: str, message: str) -> None:
        self.errors.append(ValidationFinding(severity="error", path=path, message=message))

    def add_warning(self, path: str, message: str) -> None:
        self.warnings.append(ValidationFinding(severity="warning", path=path, message=message))

    @property
    def ok(self) -> bool:
        return not self.errors


class ArtifactValidationError(ValueError):
    """Raised when a canonical artifact fails pre-write validation."""


def validate_card_write(markdown: str, *, source_path: str | Path | None = None) -> KnowledgeCard:
    try:
        return validate_card_markdown(markdown, source_path=source_path)
    except (SchemaParseError, ValidationError) as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_ref_write(payload: object, *, relative_path: str | Path | None = None) -> ReferenceRecord:
    try:
        ref = ReferenceRecord.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc
    if relative_path is not None and ref.id != Path(relative_path).stem:
        raise ArtifactValidationError("ref id must match the JSON filename")
    return ref


def validate_connections_write(payload: object) -> ConnectionsFile:
    try:
        return ConnectionsFile.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_domains_write(payload: object) -> DomainsRegistry:
    try:
        return DomainsRegistry.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_governance_write(payload: object) -> GovernanceConfig:
    try:
        return GovernanceConfig.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_search_seeds_write(payload: object) -> SearchSeedsFile:
    try:
        return SearchSeedsFile.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_event_write(payload: object) -> EventRecord:
    try:
        return EventRecord.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactValidationError(str(exc)) from exc


def validate_workspace(root: str | Path) -> ValidationReport:
    loader = WorkspaceLoader(root)
    report = ValidationReport()

    for item in loader.canonical_requirements():
        if not item.exists:
            report.add_error(item.relative_path, "missing required canonical path")

    registry = None
    valid_domains: set[str] = set()
    domain_categories: dict[str, set[str]] = {}
    if loader.resolve("domains.yaml").exists():
        try:
            registry = loader.load_domains_registry()
            valid_domains = set(registry.domains)
            domain_categories = {
                domain_id: set(entry.content_categories) for domain_id, entry in registry.domains.items()
            }
        except WorkspaceLoadError as exc:
            report.add_error("domains.yaml", str(exc))

    if loader.resolve(".construct/model-routing.yaml").exists():
        try:
            loader.load_model_routing()
        except WorkspaceLoadError as exc:
            report.add_error(".construct/model-routing.yaml", str(exc))

    if loader.resolve("governance.yaml").exists():
        try:
            loader.load_governance()
        except WorkspaceLoadError as exc:
            report.add_error("governance.yaml", str(exc))

    search_cluster_ids: set[str] = set()
    if loader.resolve("search-seeds.json").exists():
        try:
            search_seeds = loader.load_search_seeds()
        except WorkspaceLoadError as exc:
            report.add_error("search-seeds.json", str(exc))
        else:
            search_cluster_ids = {cluster.id for cluster in search_seeds.clusters}
            for cluster in search_seeds.clusters:
                if cluster.domain not in valid_domains:
                    report.add_error(
                        "search-seeds.json",
                        f"cluster '{cluster.id}' references unknown domain '{cluster.domain}'",
                    )

    connections = None
    if loader.resolve("connections.json").exists():
        try:
            connections = loader.load_connections()
        except WorkspaceLoadError as exc:
            report.add_error("connections.json", str(exc))

    valid_cards: dict[str, tuple[str, object]] = {}
    for card_path in loader.iter_cards():
        relative_path = card_path.relative_to(loader.root).as_posix()
        markdown = card_path.read_text()
        try:
            card, body = parse_card_markdown(markdown, source_path=card_path)
        except (SchemaParseError, ValidationError) as exc:
            report.add_error(relative_path, str(exc))
            continue

        if "## Summary" not in body:
            report.add_warning(relative_path, "card is missing the required ## Summary section")

        for domain in card.domains:
            if domain not in valid_domains:
                report.add_error(relative_path, f"card domain '{domain}' is not defined in domains.yaml")
        for category in card.content_categories:
            if not any(category in categories for categories in domain_categories.values()):
                report.add_error(relative_path, f"card content category '{category}' is not defined in domains.yaml")

        valid_cards[card.id] = (relative_path, card)

    for relative_path, card in valid_cards.values():
        for connection in card.connects_to:
            if connection.target not in valid_cards:
                report.add_warning(relative_path, f"connects_to target '{connection.target}' is not present in cards/")

    if connections is not None:
        for connection in connections.connections:
            if connection.from_ not in valid_cards or connection.to not in valid_cards:
                report.add_error(
                    "connections.json",
                    f"connection '{connection.from_}' -> '{connection.to}' references a missing card",
                )

    for ref_path in loader.iter_refs():
        relative_path = ref_path.relative_to(loader.root).as_posix()
        try:
            ref = validate_ref_write(loader.read_json(relative_path), relative_path=relative_path)
        except (ArtifactValidationError, WorkspaceLoadError) as exc:
            report.add_error(relative_path, str(exc))
            continue
        if ref.domain not in valid_domains:
            report.add_error(relative_path, f"ref domain '{ref.domain}' is not defined in domains.yaml")
        if search_cluster_ids and ref.search_cluster not in search_cluster_ids:
            report.add_error(relative_path, f"ref search cluster '{ref.search_cluster}' is not defined in search-seeds.json")
        for card_id in ref.cards_generated:
            if card_id not in valid_cards:
                report.add_warning(relative_path, f"generated card '{card_id}' is not present in cards/")

    events_path = loader.resolve("log/events.jsonl")
    if events_path.exists():
        for line_number, line in enumerate(events_path.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = loader.parse_event_line(line, line_number=line_number)
            except WorkspaceLoadError as exc:
                report.add_error("log/events.jsonl", str(exc))
                continue
            if event.target and event.target not in valid_cards and event.target not in valid_domains:
                report.add_warning(
                    "log/events.jsonl",
                    f"event target '{event.target}' does not match a known card or domain",
                )

    return report
