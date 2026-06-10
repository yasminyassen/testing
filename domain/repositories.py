"""
Repository Interfaces — abstract contracts defined in the domain layer.

The domain depends on these abstractions; infrastructure implements them.
This inverts the dependency so the domain never touches persistence details.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from clean_inventory.domain.entities import Product
from clean_inventory.domain.value_objects import SKU


class AbstractProductRepository(ABC):
    """Persistence contract for the Product aggregate."""

    @abstractmethod
    def save(self, product: Product) -> None:
        """Persist a new or updated product."""

    @abstractmethod
    def find_by_id(self, product_id: UUID) -> Optional[Product]:
        """Return the product with *product_id*, or None if absent."""

    @abstractmethod
    def find_by_sku(self, sku: SKU) -> Optional[Product]:
        """Return the product whose SKU matches, or None if absent."""

    @abstractmethod
    def find_all_active(self) -> List[Product]:
        """Return every active product."""

    @abstractmethod
    def find_below_reorder_threshold(self) -> List[Product]:
        """Return active products whose stock is at or below their reorder threshold."""

    @abstractmethod
    def delete(self, product_id: UUID) -> None:
        """Permanently remove a product record."""
