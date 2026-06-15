"""Views data contract models and generator pipeline.

Versioning lives in two intentional, separate places: the views
data-contract version (the ``schema_version`` field on ``ViewsEnvelope``)
and the package version (``construct.__version__``). This module
deliberately carries no ``__version__`` of its own, so there is no third
version to drift.
"""

from __future__ import annotations

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
