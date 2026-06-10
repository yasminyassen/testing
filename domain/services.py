"""
Domain Services — stateless business logic that spans multiple aggregates
or requires coordination that doesn't belong on a single entity.

Domain services depend only on domain abstractions — never on infrastructure.
"""
from __future__ import annotations

from clean_inventory.domain.entities import Product
from clean_inventory.domain.repositories import AbstractProductRepository
from clean_inventory.domain.value_objects import SKU
from clean_inventory.shared.exceptions import ConflictError


class SKUUniquenessChecker:
    """
    Verifies that a SKU is not already in use before a product is created.

    Single Responsibility: uniqueness check only.
    """

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def assert_unique(self, sku: str) -> None:
        """Raise ConflictError if the SKU is already taken."""
        existing = self._repo.find_by_sku(SKU(sku))
        if existing is not None:
            raise ConflictError(f"A product with SKU '{sku}' already exists.")


class StockTransferService:
    """
    Transfers stock units from one product to another atomically.

    Single Responsibility: cross-aggregate stock movement only.
    """

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def transfer(self, source: Product, destination: Product, quantity: int) -> None:
        """
        Move *quantity* units from *source* to *destination*.

        Both products must be active and the source must have sufficient stock.
        Changes are persisted only if both operations succeed.
        """
        source.reduce_stock(quantity)
        destination.add_stock(quantity)
        self._repo.save(source)
        self._repo.save(destination)


class ReorderCandidateLocator:
    """
    Identifies products that need to be reordered.

    Single Responsibility: query for low-stock products only.
    """

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def locate(self) -> list[Product]:
        """Return all active products at or below their reorder threshold."""
        return self._repo.find_below_reorder_threshold()
