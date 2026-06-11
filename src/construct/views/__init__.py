"""Views data contract models and generator pipeline."""

from __future__ import annotations

__version__ = "0.1.0"

from .models import (
    ArticleRecord,
    ArticlesFile,
    BridgeRecord,
    BridgesFile,
    BridgeSummary,
    CardRecord,
    CardsFile,
    ConnectionRecord,
    ConnectionsFile,
    DigestRecord,
    DigestsFile,
    DomainRecord,
    DomainsFile,
    EventRecord,
    EventsFile,
    StatsFile,
    ViewsEnvelope,
    schema_for,
    validate_data,
)

__all__ = [
    "ArticleRecord",
    "ArticlesFile",
    "BridgeRecord",
    "BridgesFile",
    "BridgeSummary",
    "CardRecord",
    "CardsFile",
    "ConnectionRecord",
    "ConnectionsFile",
    "DigestRecord",
    "DigestsFile",
    "DomainRecord",
    "DomainsFile",
    "EventRecord",
    "EventsFile",
    "StatsFile",
    "ViewsEnvelope",
    "schema_for",
    "validate_data",
]
