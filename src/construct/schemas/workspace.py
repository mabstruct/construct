"""Workspace scaffold and authoritative connections schema."""

from __future__ import annotations

from datetime import date
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

REQUIRED_PATHS = (
    "cards",
    "domains",
    "domains.yaml",
    "connections.json",
    "governance.yaml",
    "model-routing.yaml",
    "refs",
    "workflows",
    "log/events.jsonl",
    "inbox",
    "digests",
    "db",
    "views",
    "publish",
)


class ConnectionType(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    extends = "extends"
    parallels = "parallels"
    requires = "requires"
    enables = "enables"
    challenges = "challenges"
    inspires = "inspires"
    gap_for = "gap-for"


class ConnectionAuthor(str, Enum):
    curator = "curator"
    human = "human"
    researcher = "researcher"


class ConnectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: str = Field(alias="from")
    to: str
    type: ConnectionType
    note: str | None = None
    created: date
    created_by: ConnectionAuthor

    @field_validator("from_", "to")
    @classmethod
    def validate_card_id(cls, value: str) -> str:
        if not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("connection endpoints must be kebab-case card ids")
        return value


class ConnectionsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    updated: date
    connection_types: list[ConnectionType]
    connections: list[ConnectionRecord]

    @model_validator(mode="after")
    def validate_no_duplicates(self) -> "ConnectionsFile":
        seen: set[tuple[str, str, ConnectionType]] = set()
        for connection in self.connections:
            key = (connection.from_, connection.to, connection.type)
            if key in seen:
                raise ValueError("duplicate canonical connections are not allowed")
            seen.add(key)
        return self


class WorkspaceScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_paths: tuple[str, ...] = REQUIRED_PATHS
    canonical_paths: tuple[str, ...] = (
        "cards",
        "domains.yaml",
        "domains/**/domain.yaml",
        "connections.json",
        "governance.yaml",
        "model-routing.yaml",
        "refs",
        "workflows",
        "log/events.jsonl",
    )
    derived_paths: tuple[str, ...] = ("db", "views")
    support_paths: tuple[str, ...] = ("inbox", "digests", "publish")
