"""
Domain Events — immutable records of things that happened in the domain.

Events flow outward (domain → application → infrastructure).
Nothing in this module imports from application or infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from clean_inventory.shared.utils import utc_now, new_id


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID = field(default_factory=new_id)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ProductCreated(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    sku: str = ""
    name: str = ""


@dataclass(frozen=True)
class StockAdded(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    quantity_added: int = 0
    new_total: int = 0


@dataclass(frozen=True)
class StockReduced(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    quantity_removed: int = 0
    new_total: int = 0


@dataclass(frozen=True)
class ReorderAlertTriggered(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    sku: str = ""
    current_quantity: int = 0
    threshold: int = 0


@dataclass(frozen=True)
class ProductPriceUpdated(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    old_price_amount: str = ""
    new_price_amount: str = ""
    currency: str = "USD"


@dataclass(frozen=True)
class ProductDeactivated(DomainEvent):
    product_id: UUID = field(default_factory=new_id)
    reason: str = ""
