"""Knowledge card schema and markdown parsing helpers."""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SchemaParseError(ValueError):
    """Raised when a canonical markdown or YAML document cannot be parsed."""


class EpistemicType(str, Enum):
    finding = "finding"
    claim = "claim"
    concept = "concept"
    method = "method"
    paper = "paper"
    theme = "theme"
    gap = "gap"
    provocation = "provocation"
    question = "question"
    connection = "connection"


class Lifecycle(str, Enum):
    seed = "seed"
    growing = "growing"
    mature = "mature"
    archived = "archived"


class SourceType(str, Enum):
    paper = "paper"
    url = "url"
    digest = "digest"
    observation = "observation"
    conversation = "conversation"


class ConnectionRelation(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    extends = "extends"
    parallels = "parallels"
    requires = "requires"
    enables = "enables"
    challenges = "challenges"
    inspires = "inspires"
    gap_for = "gap-for"


class CardAuthor(str, Enum):
    construct = "construct"
    curator = "curator"
    researcher = "researcher"
    human = "human"


class CardSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SourceType
    ref: str
    title: str | None = None


class CardConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    relation: ConnectionRelation
    note: str | None = None

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        if not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("target must be kebab-case")
        return value


class KnowledgeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    epistemic_type: EpistemicType
    created: date
    confidence: int = Field(ge=1, le=5)
    source_tier: int = Field(ge=1, le=5)
    domains: list[str] = Field(min_length=1)
    content_categories: list[str] = Field(default_factory=list)
    lifecycle: Lifecycle = Lifecycle.seed
    sources: list[CardSource] = Field(default_factory=list)
    connects_to: list[CardConnection] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    author: CardAuthor | None = None
    last_verified: date | None = None
    promoted_from: str | None = None
    supersedes: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if len(value) > 80 or not KEBAB_CASE_PATTERN.fullmatch(value):
            raise ValueError("id must be kebab-case and <= 80 characters")
        return value

    @field_validator("domains", "content_categories", "tags")
    @classmethod
    def validate_kebab_lists(cls, values: list[str]) -> list[str]:
        for value in values:
            if not KEBAB_CASE_PATTERN.fullmatch(value):
                raise ValueError("entries must be kebab-case, e.g. 'quantum-gravity' not 'quantum gravity'")
        return values


def _split_frontmatter(markdown: str) -> tuple[str, str]:
    if not markdown.startswith("---\n"):
        raise SchemaParseError("markdown card is missing YAML frontmatter")

    parts = markdown.split("\n---\n", 1)
    if len(parts) != 2:
        raise SchemaParseError("markdown card frontmatter is not properly terminated")

    return parts[0][4:], parts[1]


def parse_card_markdown(markdown: str, *, source_path: str | Path | None = None) -> tuple[KnowledgeCard, str]:
    frontmatter_text, body = _split_frontmatter(markdown)
    yaml = YAML(typ="safe")

    try:
        frontmatter = yaml.load(frontmatter_text) or {}
    except YAMLError as exc:
        raise SchemaParseError(f"invalid YAML frontmatter: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise SchemaParseError("card frontmatter must parse to a mapping")

    try:
        card = KnowledgeCard.model_validate(frontmatter)
    except ValidationError:
        raise

    if source_path is not None:
        source_name = Path(source_path).stem
        if card.id != source_name:
            raise SchemaParseError("card id must match the markdown filename")

    return card, body
