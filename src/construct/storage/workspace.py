"""Workspace discovery and canonical file loading."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from construct.schemas.card import SchemaParseError, parse_card_markdown
from construct.schemas.config import (
    DomainConfig,
    DomainsRegistry,
    EventRecord,
    GovernanceConfig,
    ModelRoutingConfig,
    ReferenceRecord,
    SearchConfig,
    SearchSeedsFile,
)
from construct.schemas.workspace import ConnectionsFile, WorkspaceScaffold


@dataclass(frozen=True)
class WorkspaceItem:
    relative_path: str
    category: str
    exists: bool


class WorkspaceLoadError(ValueError):
    """Raised when a workspace file cannot be parsed into a schema."""


#: The file whose presence marks a directory as a CONSTRUCT workspace. It is the
#: domain registry every canonical read goes through, it is in
#: ``WorkspaceScaffold.required_paths``, and ``initialize_workspace`` writes it —
#: so "has this" and "was scaffolded by us" are the same statement.
WORKSPACE_MARKER = "domains.yaml"


def workspace_error(workspace: Path | str) -> str | None:
    """Return why *workspace* is not a CONSTRUCT workspace, or ``None``.

    The workspace analogue of ``views.generate.install_root_error``, and it exists
    for the identical reason, one layer down. Registration is what makes a
    ``workspace`` argument *agent-supplied* over MCP (and, from Phase 19, over
    HTTP), so the marker check stops being an internal convenience and becomes a
    boundary control. Every capability that WRITES under an agent-supplied
    workspace must call this before touching the filesystem: the write services
    create ``cards/`` and ``log/`` under whatever they are handed, so an unguarded
    path argument is a primitive for creating directories and writing
    attacker-influenced markdown/JSONL anywhere the process can write — and it
    reports ``success: true`` afterwards (CR-04).

    The returned reason deliberately does **not** embed the path, following the
    ``install_root_error`` convention: a caller that must not echo filesystem
    locations (the MCP surface) can surface it verbatim, while a local caller
    (the CLI) appends the path itself.
    """
    root = Path(workspace)
    if not root.is_dir():
        return "workspace is not an existing directory"
    if not (root / WORKSPACE_MARKER).is_file():
        return f"not a CONSTRUCT workspace: missing {WORKSPACE_MARKER}"
    return None


class WorkspaceLoader:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.scaffold = WorkspaceScaffold()
        self._yaml = YAML(typ="safe")

    def resolve(self, relative_path: str) -> Path:
        return self.root / PurePosixPath(relative_path)

    def classify(self, relative_path: str) -> str:
        pure = PurePosixPath(relative_path)
        for pattern in self.scaffold.canonical_paths:
            if pure.match(pattern):
                return "canonical"
        for pattern in self.scaffold.derived_paths:
            if pure.match(pattern) or str(pure).startswith(f"{pattern}/"):
                return "derived"
        for pattern in self.scaffold.support_paths:
            if pure.match(pattern) or str(pure).startswith(f"{pattern}/"):
                return "support"
        return "unknown"

    def inspect_workspace(self) -> list[WorkspaceItem]:
        return [
            WorkspaceItem(relative_path=path, category=self.classify(path), exists=self.resolve(path).exists())
            for path in self.scaffold.required_paths
        ]

    def canonical_requirements(self) -> list[WorkspaceItem]:
        return [item for item in self.inspect_workspace() if item.category == "canonical"]

    def read_yaml(self, relative_path: str) -> object:
        path = self.resolve(relative_path)
        try:
            return self._yaml.load(path.read_text())
        except YAMLError as exc:
            raise WorkspaceLoadError(f"invalid YAML in {relative_path}: {exc}") from exc

    def read_json(self, relative_path: str) -> object:
        path = self.resolve(relative_path)
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise WorkspaceLoadError(f"invalid JSON in {relative_path}: {exc}") from exc

    def load_domains_registry(self) -> DomainsRegistry:
        try:
            return DomainsRegistry.model_validate(self.read_yaml("domains.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid domains.yaml: {exc}") from exc

    def load_domain_config(self, relative_path: str) -> DomainConfig:
        try:
            return DomainConfig.model_validate(self.read_yaml(relative_path))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid {relative_path}: {exc}") from exc

    def load_model_routing(self) -> ModelRoutingConfig:
        try:
            return ModelRoutingConfig.model_validate(self.read_yaml(".construct/model-routing.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid .construct/model-routing.yaml: {exc}") from exc

    def load_search_config(self) -> SearchConfig:
        try:
            return SearchConfig.model_validate(self.read_yaml(".construct/search.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid .construct/search.yaml: {exc}") from exc

    def load_governance(self) -> GovernanceConfig:
        try:
            return GovernanceConfig.model_validate(self.read_yaml("governance.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid governance.yaml: {exc}") from exc

    def load_search_seeds(self) -> SearchSeedsFile:
        try:
            return SearchSeedsFile.model_validate(self.read_json("search-seeds.json"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid search-seeds.json: {exc}") from exc

    def load_connections(self) -> ConnectionsFile:
        try:
            return ConnectionsFile.model_validate(self.read_json("connections.json"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid connections.json: {exc}") from exc

    def load_ref(self, relative_path: str) -> ReferenceRecord:
        try:
            return ReferenceRecord.model_validate(self.read_json(relative_path))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid {relative_path}: {exc}") from exc

    def parse_event_line(self, line: str, *, line_number: int) -> EventRecord:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkspaceLoadError(f"invalid log/events.jsonl line {line_number}: {exc}") from exc
        try:
            return EventRecord.model_validate(payload)
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid log/events.jsonl line {line_number}: {exc}") from exc

    def iter_cards(self) -> list[Path]:
        cards_dir = self.resolve("cards")
        if not cards_dir.exists():
            return []
        return sorted(cards_dir.glob("*.md"))

    def load_cards(self) -> list[dict]:
        """Load and parse all cards from the workspace.

        Returns a list of dicts with card metadata and body text. Recency anchors
        (``created`` / ``last_verified``) stay as ``datetime.date`` objects
        (python-mode dump — consumers such as the curation decay/orphan scans rely
        on that), but ``lifecycle`` is normalized to its plain string value rather
        than the ``Lifecycle`` enum member so callers get a stable serializable
        token (``"growing"`` not ``"Lifecycle.growing"``). ``Lifecycle`` is a
        ``(str, Enum)`` so any existing ``== Lifecycle.X`` / ``.value`` comparison
        keeps working against the string form. Unparseable cards are skipped.
        """
        cards: list[dict] = []
        for card_path in self.iter_cards():
            try:
                markdown = card_path.read_text(encoding="utf-8")
                card, body = parse_card_markdown(markdown, source_path=card_path)
                card_data = card.model_dump()
                # Normalize lifecycle to its serializable string value (enum → str).
                lifecycle = card_data.get("lifecycle")
                card_data["lifecycle"] = getattr(lifecycle, "value", lifecycle)
                card_data["body"] = body
                cards.append(card_data)
            except (SchemaParseError, OSError):
                import warnings
                warnings.warn(f"Skipping unparseable card: {card_path}")
                continue
        return cards

    def iter_refs(self) -> list[Path]:
        refs_dir = self.resolve("refs")
        if not refs_dir.exists():
            return []
        return sorted(refs_dir.glob("*.json"))
