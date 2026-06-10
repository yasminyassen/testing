"""
Domain Entities and Aggregate Roots.

Rules:
- Each entity owns its own invariants.
- Aggregates collect domain events internally; the application layer drains them.
- No entity imports from application, infrastructure, or presentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID

from clean_inventory.domain.events import (
    DomainEvent,
    ProductCreated,
    ProductDeactivated,
    ProductPriceUpdated,
    ReorderAlertTriggered,
    StockAdded,
    StockReduced,
)
from clean_inventory.domain.value_objects import (
    Money,
    ProductName,
    Quantity,
    ReorderThreshold,
    SKU,
)
from clean_inventory.shared.exceptions import ConflictError, ValidationError
from clean_inventory.shared.utils import new_id, utc_now


# ---------------------------------------------------------------------------
# Product (Aggregate Root)
# ---------------------------------------------------------------------------


@dataclass
class Product:
    """
    Aggregate root for the Product bounded context.

    Enforces all stock and pricing invariants.
    Collects domain events for the application layer to dispatch.
    """

    id: UUID
    sku: SKU
    name: ProductName
    price: Money
    stock: Quantity
    reorder_threshold: ReorderThreshold
    is_active: bool
    created_at: datetime
    updated_at: datetime

    _events: List[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        sku: str,
        name: str,
        price_amount: str,
        currency: str = "USD",
        initial_stock: int = 0,
        reorder_threshold: int = 0,
    ) -> "Product":
        now = utc_now()
        product = cls(
            id=new_id(),
            sku=SKU(sku),
            name=ProductName(name),
            price=Money.of(price_amount, currency),
            stock=Quantity(initial_stock),
            reorder_threshold=ReorderThreshold(reorder_threshold),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        product._record(
            ProductCreated(
                product_id=product.id,
                sku=str(product.sku),
                name=str(product.name),
            )
        )
        return product

    # ------------------------------------------------------------------
    # Stock commands
    # ------------------------------------------------------------------

    def add_stock(self, quantity: int) -> None:
        """Increase on-hand stock by *quantity* units."""
        self._assert_active()
        added = Quantity(quantity)
        self.stock = self.stock.add(added)
        self._touch()
        self._record(
            StockAdded(
                product_id=self.id,
                quantity_added=quantity,
                new_total=self.stock.value,
            )
        )

    def reduce_stock(self, quantity: int) -> None:
        """Decrease on-hand stock by *quantity* units."""
        self._assert_active()
        removed = Quantity(quantity)
        self.stock = self.stock.subtract(removed)
        self._touch()
        self._record(
            StockReduced(
                product_id=self.id,
                quantity_removed=quantity,
                new_total=self.stock.value,
            )
        )
        self._check_reorder_threshold()

    # ------------------------------------------------------------------
    # Price command
    # ------------------------------------------------------------------

    def update_price(self, new_amount: str, currency: str | None = None) -> None:
        """Replace the current price with a new one."""
        self._assert_active()
        old_price = self.price
        self.price = Money.of(new_amount, currency or self.price.currency)
        self._touch()
        self._record(
            ProductPriceUpdated(
                product_id=self.id,
                old_price_amount=str(old_price.amount),
                new_price_amount=str(self.price.amount),
                currency=self.price.currency,
            )
        )

    # ------------------------------------------------------------------
    # Lifecycle commands
    # ------------------------------------------------------------------

    def deactivate(self, reason: str = "") -> None:
        """Mark this product as inactive so it can no longer be sold."""
        if not self.is_active:
            raise ConflictError(f"Product '{self.sku}' is already inactive.")
        self.is_active = False
        self._touch()
        self._record(ProductDeactivated(product_id=self.id, reason=reason))

    # ------------------------------------------------------------------
    # Event drain
    # ------------------------------------------------------------------

    def pull_events(self) -> List[DomainEvent]:
        """Return and clear all pending domain events."""
        events, self._events = list(self._events), []
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assert_active(self) -> None:
        if not self.is_active:
            raise ConflictError(f"Product '{self.sku}' is inactive and cannot be modified.")

    def _check_reorder_threshold(self) -> None:
        if self.reorder_threshold.is_breached_by(self.stock):
            self._record(
                ReorderAlertTriggered(
                    product_id=self.id,
                    sku=str(self.sku),
                    current_quantity=self.stock.value,
                    threshold=self.reorder_threshold.value,
                )
            )

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def _touch(self) -> None:
        self.updated_at = utc_now()
