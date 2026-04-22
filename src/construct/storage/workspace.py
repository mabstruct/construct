"""Workspace discovery and canonical file loading."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from construct.schemas.config import DomainConfig, DomainsRegistry, GovernanceConfig, ModelRoutingConfig
from construct.schemas.workspace import ConnectionsFile, WorkspaceScaffold


@dataclass(frozen=True)
class WorkspaceItem:
    relative_path: str
    category: str
    exists: bool


class WorkspaceLoadError(ValueError):
    """Raised when a workspace file cannot be parsed into a schema."""


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
            return ModelRoutingConfig.model_validate(self.read_yaml("model-routing.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid model-routing.yaml: {exc}") from exc

    def load_governance(self) -> GovernanceConfig:
        try:
            return GovernanceConfig.model_validate(self.read_yaml("governance.yaml"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid governance.yaml: {exc}") from exc

    def load_connections(self) -> ConnectionsFile:
        try:
            return ConnectionsFile.model_validate(self.read_json("connections.json"))
        except ValidationError as exc:
            raise WorkspaceLoadError(f"invalid connections.json: {exc}") from exc

    def iter_cards(self) -> list[Path]:
        cards_dir = self.resolve("cards")
        if not cards_dir.exists():
            return []
        return sorted(cards_dir.glob("*.md"))
