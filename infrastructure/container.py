"""
Dependency Injection Container — wires the entire object graph.

This is the ONLY place where concrete classes are named.
Every other module depends only on abstractions.

Open/Closed: swap any component by changing this file alone.
"""
from __future__ import annotations

from clean_inventory.application.interfaces import AbstractEventPublisher, AbstractLogger
from clean_inventory.application.use_cases import (
    AddStockUseCase,
    CreateProductUseCase,
    DeactivateProductUseCase,
    GetProductBySkuUseCase,
    GetProductUseCase,
    GetReorderCandidatesUseCase,
    ListActiveProductsUseCase,
    ReduceStockUseCase,
    TransferStockUseCase,
    UpdatePriceUseCase,
)
from clean_inventory.domain.repositories import AbstractProductRepository
from clean_inventory.infrastructure.messaging import ConsoleLogger, InProcessEventPublisher
from clean_inventory.infrastructure.persistence import InMemoryProductRepository


class Container:
    """
    Manual DI container.

    All dependencies are instantiated once (singleton scope) and injected
    into use cases through their constructors — never through globals or
    service-locator lookups.
    """

    def __init__(
        self,
        repository: AbstractProductRepository | None = None,
        event_publisher: AbstractEventPublisher | None = None,
        logger: AbstractLogger | None = None,
    ) -> None:
        # Infrastructure (swappable via constructor overrides)
        self.repository: AbstractProductRepository = repository or InMemoryProductRepository()
        self.event_publisher: AbstractEventPublisher = event_publisher or InProcessEventPublisher()
        self.logger: AbstractLogger = logger or ConsoleLogger()

        # Application use cases (depend only on the abstractions above)
        self.create_product = CreateProductUseCase(
            self.repository, self.event_publisher, self.logger
        )
        self.get_product = GetProductUseCase(self.repository)
        self.get_product_by_sku = GetProductBySkuUseCase(self.repository)
        self.list_active_products = ListActiveProductsUseCase(self.repository)
        self.add_stock = AddStockUseCase(self.repository, self.event_publisher, self.logger)
        self.reduce_stock = ReduceStockUseCase(self.repository, self.event_publisher, self.logger)
        self.transfer_stock = TransferStockUseCase(
            self.repository, self.event_publisher, self.logger
        )
        self.update_price = UpdatePriceUseCase(self.repository, self.event_publisher, self.logger)
        self.deactivate_product = DeactivateProductUseCase(
            self.repository, self.event_publisher, self.logger
        )
        self.get_reorder_candidates = GetReorderCandidatesUseCase(self.repository)
