"""
Infrastructure — In-Memory Repository Implementation.

Implements the domain's AbstractProductRepository contract using a plain dict.
Swappable: replace with SQLProductRepository, MongoProductRepository, etc.
without touching domain or application code.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from clean_inventory.domain.entities import Product
from clean_inventory.domain.repositories import AbstractProductRepository
from clean_inventory.domain.value_objects import SKU


class InMemoryProductRepository(AbstractProductRepository):
    """
    Thread-unsafe in-memory store — suitable for tests and local demos.

    Open/Closed: adding a new query method is an extension, not a modification.
    """

    def __init__(self) -> None:
        self._store: Dict[UUID, Product] = {}

    # ------------------------------------------------------------------
    # AbstractProductRepository interface
    # ------------------------------------------------------------------

    def save(self, product: Product) -> None:
        self._store[product.id] = product

    def find_by_id(self, product_id: UUID) -> Optional[Product]:
        return self._store.get(product_id)

    def find_by_sku(self, sku: SKU) -> Optional[Product]:
        for product in self._store.values():
            if product.sku == sku:
                return product
        return None

    def find_all_active(self) -> List[Product]:
        return [p for p in self._store.values() if p.is_active]

    def find_below_reorder_threshold(self) -> List[Product]:
        return [
            p
            for p in self._store.values()
            if p.is_active and p.reorder_threshold.is_breached_by(p.stock)
        ]

    def delete(self, product_id: UUID) -> None:
        self._store.pop(product_id, None)

    # ------------------------------------------------------------------
    # Convenience (non-interface)
    # ------------------------------------------------------------------

    def count(self) -> int:
        return len(self._store)
