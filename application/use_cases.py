"""
Application Use Cases — one class per business action, no exceptions.

Each use case:
  1. Accepts a single command/query DTO.
  2. Orchestrates domain objects and services.
  3. Drains and publishes domain events.
  4. Returns a typed response DTO.

Use cases never contain business logic — that lives in the domain.
Use cases never touch infrastructure directly — they use abstract interfaces.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from clean_inventory.application.dtos import (
    AddStockCommand,
    CreateProductCommand,
    DeactivateProductCommand,
    GetProductBySkuQuery,
    GetProductQuery,
    ProductResponse,
    ReduceStockCommand,
    TransferStockCommand,
    UpdatePriceCommand,
)
from clean_inventory.application.interfaces import AbstractEventPublisher, AbstractLogger
from clean_inventory.domain.entities import Product
from clean_inventory.domain.repositories import AbstractProductRepository
from clean_inventory.domain.services import (
    ReorderCandidateLocator,
    SKUUniquenessChecker,
    StockTransferService,
)
from clean_inventory.domain.value_objects import SKU
from clean_inventory.shared.exceptions import NotFoundError


def _to_response(product: Product) -> ProductResponse:
    """Map a Product aggregate to a safe response DTO."""
    return ProductResponse(
        id=product.id,
        sku=str(product.sku),
        name=str(product.name),
        price_amount=product.price.amount,
        currency=product.price.currency,
        stock=product.stock.value,
        reorder_threshold=product.reorder_threshold.value,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _require_product(repo: AbstractProductRepository, product_id: UUID) -> Product:
    """Fetch a product or raise NotFoundError."""
    product = repo.find_by_id(product_id)
    if product is None:
        raise NotFoundError(f"Product '{product_id}' not found.")
    return product


# ---------------------------------------------------------------------------
# Create Product
# ---------------------------------------------------------------------------


class CreateProductUseCase:
    """Register a new product in the inventory catalogue."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger
        self._uniqueness_checker = SKUUniquenessChecker(repository)

    def execute(self, command: CreateProductCommand) -> ProductResponse:
        self._uniqueness_checker.assert_unique(command.sku)
        product = Product.create(
            sku=command.sku,
            name=command.name,
            price_amount=command.price_amount,
            currency=command.currency,
            initial_stock=command.initial_stock,
            reorder_threshold=command.reorder_threshold,
        )
        self._repo.save(product)
        self._publisher.publish_all(product.pull_events())
        self._logger.info("Product created", sku=command.sku, product_id=str(product.id))
        return _to_response(product)


# ---------------------------------------------------------------------------
# Get Product
# ---------------------------------------------------------------------------


class GetProductUseCase:
    """Retrieve a single product by its ID."""

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def execute(self, query: GetProductQuery) -> ProductResponse:
        product = _require_product(self._repo, query.product_id)
        return _to_response(product)


class GetProductBySkuUseCase:
    """Retrieve a single product by its SKU."""

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def execute(self, query: GetProductBySkuQuery) -> ProductResponse:
        product = self._repo.find_by_sku(SKU(query.sku))
        if product is None:
            raise NotFoundError(f"Product with SKU '{query.sku}' not found.")
        return _to_response(product)


# ---------------------------------------------------------------------------
# List All Active Products
# ---------------------------------------------------------------------------


class ListActiveProductsUseCase:
    """Return all active products."""

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository

    def execute(self) -> List[ProductResponse]:
        return [_to_response(p) for p in self._repo.find_all_active()]


# ---------------------------------------------------------------------------
# Add Stock
# ---------------------------------------------------------------------------


class AddStockUseCase:
    """Increase the on-hand stock of a product."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger

    def execute(self, command: AddStockCommand) -> ProductResponse:
        product = _require_product(self._repo, command.product_id)
        product.add_stock(command.quantity)
        self._repo.save(product)
        self._publisher.publish_all(product.pull_events())
        self._logger.info(
            "Stock added",
            product_id=str(command.product_id),
            quantity=command.quantity,
        )
        return _to_response(product)


# ---------------------------------------------------------------------------
# Reduce Stock
# ---------------------------------------------------------------------------


class ReduceStockUseCase:
    """Decrease the on-hand stock of a product (e.g. after a sale)."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger

    def execute(self, command: ReduceStockCommand) -> ProductResponse:
        product = _require_product(self._repo, command.product_id)
        product.reduce_stock(command.quantity)
        self._repo.save(product)
        self._publisher.publish_all(product.pull_events())
        self._logger.info(
            "Stock reduced",
            product_id=str(command.product_id),
            quantity=command.quantity,
        )
        return _to_response(product)


# ---------------------------------------------------------------------------
# Transfer Stock
# ---------------------------------------------------------------------------


class TransferStockUseCase:
    """Move stock units from one product to another."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger
        self._transfer_service = StockTransferService(repository)

    def execute(self, command: TransferStockCommand) -> None:
        source = _require_product(self._repo, command.source_product_id)
        destination = _require_product(self._repo, command.destination_product_id)
        self._transfer_service.transfer(source, destination, command.quantity)
        self._publisher.publish_all(source.pull_events())
        self._publisher.publish_all(destination.pull_events())
        self._logger.info(
            "Stock transferred",
            source=str(command.source_product_id),
            destination=str(command.destination_product_id),
            quantity=command.quantity,
        )


# ---------------------------------------------------------------------------
# Update Price
# ---------------------------------------------------------------------------


class UpdatePriceUseCase:
    """Change the unit price of a product."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger

    def execute(self, command: UpdatePriceCommand) -> ProductResponse:
        product = _require_product(self._repo, command.product_id)
        product.update_price(command.new_amount, command.currency)
        self._repo.save(product)
        self._publisher.publish_all(product.pull_events())
        self._logger.info(
            "Price updated",
            product_id=str(command.product_id),
            new_amount=command.new_amount,
        )
        return _to_response(product)


# ---------------------------------------------------------------------------
# Deactivate Product
# ---------------------------------------------------------------------------


class DeactivateProductUseCase:
    """Remove a product from active sale."""

    def __init__(
        self,
        repository: AbstractProductRepository,
        event_publisher: AbstractEventPublisher,
        logger: AbstractLogger,
    ) -> None:
        self._repo = repository
        self._publisher = event_publisher
        self._logger = logger

    def execute(self, command: DeactivateProductCommand) -> ProductResponse:
        product = _require_product(self._repo, command.product_id)
        product.deactivate(command.reason)
        self._repo.save(product)
        self._publisher.publish_all(product.pull_events())
        self._logger.warning(
            "Product deactivated",
            product_id=str(command.product_id),
            reason=command.reason,
        )
        return _to_response(product)


# ---------------------------------------------------------------------------
# Reorder Report
# ---------------------------------------------------------------------------


class GetReorderCandidatesUseCase:
    """List all products that need to be restocked."""

    def __init__(self, repository: AbstractProductRepository) -> None:
        self._repo = repository
        self._locator = ReorderCandidateLocator(repository)

    def execute(self) -> List[ProductResponse]:
        return [_to_response(p) for p in self._locator.locate()]
