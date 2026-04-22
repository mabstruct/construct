"""Workspace validation service with structured errors and warnings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from construct.schemas.card import SchemaParseError, parse_card_markdown
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


def validate_workspace(root: str | Path) -> ValidationReport:
    loader = WorkspaceLoader(root)
    report = ValidationReport()

    for item in loader.canonical_requirements():
        if not item.exists:
            report.add_error(item.relative_path, "missing required canonical path")

    registry = None
    if loader.resolve("domains.yaml").exists():
        try:
            registry = loader.load_domains_registry()
        except WorkspaceLoadError as exc:
            report.add_error("domains.yaml", str(exc))

    if loader.resolve("model-routing.yaml").exists():
        try:
            loader.load_model_routing()
        except WorkspaceLoadError as exc:
            report.add_error("model-routing.yaml", str(exc))

    if loader.resolve("governance.yaml").exists():
        try:
            loader.load_governance()
        except WorkspaceLoadError as exc:
            report.add_error("governance.yaml", str(exc))

    if loader.resolve("connections.json").exists():
        try:
            loader.load_connections()
        except WorkspaceLoadError as exc:
            report.add_error("connections.json", str(exc))

    if registry is not None:
        for domain_id, entry in registry.domains.items():
            domain_path = entry.path
            if not loader.resolve(domain_path).exists():
                report.add_error(domain_path, f"domain registry entry '{domain_id}' points to a missing file")
                continue
            try:
                domain = loader.load_domain_config(domain_path)
            except WorkspaceLoadError as exc:
                report.add_error(domain_path, str(exc))
                continue
            if domain.id != domain_id:
                report.add_error(domain_path, f"domain id '{domain.id}' does not match registry id '{domain_id}'")

    valid_cards: dict[str, tuple[str, object]] = {}
    for card_path in loader.iter_cards():
        relative_path = card_path.relative_to(loader.root).as_posix()
        try:
            card, body = parse_card_markdown(card_path.read_text(), source_path=card_path)
        except SchemaParseError as exc:
            report.add_error(relative_path, str(exc))
            continue
        except ValidationError as exc:
            report.add_error(relative_path, str(exc))
            continue

        if "## Summary" not in body:
            report.add_warning(relative_path, "card is missing the required ## Summary section")

        valid_cards[card.id] = (relative_path, card)

    for relative_path, card in valid_cards.values():
        for connection in card.connects_to:
            if connection.target not in valid_cards:
                report.add_warning(relative_path, f"connects_to target '{connection.target}' is not present in cards/")

    return report
