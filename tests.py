"""
Test suite — validates all domain rules, use cases, and infrastructure.

Tests are organized by layer. Mocks replace infrastructure so domain
and application tests have zero I/O.
"""
from __future__ import annotations

import sys
import os

# Allow running from the parent of clean_inventory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from decimal import Decimal
from typing import List
from unittest.mock import MagicMock
from uuid import uuid4

from clean_inventory.application.dtos import (
    AddStockCommand,
    CreateProductCommand,
    DeactivateProductCommand,
    GetProductQuery,
    ReduceStockCommand,
    UpdatePriceCommand,
)
from clean_inventory.application.interfaces import AbstractEventPublisher, AbstractLogger
from clean_inventory.application.use_cases import (
    AddStockUseCase,
    CreateProductUseCase,
    DeactivateProductUseCase,
    GetProductUseCase,
    GetReorderCandidatesUseCase,
    ListActiveProductsUseCase,
    ReduceStockUseCase,
    UpdatePriceUseCase,
)
from clean_inventory.domain.entities import Product
from clean_inventory.domain.events import (
    ProductCreated,
    ReorderAlertTriggered,
    StockAdded,
    StockReduced,
)
from clean_inventory.domain.value_objects import Money, ProductName, Quantity, ReorderThreshold, SKU
from clean_inventory.infrastructure.container import Container
from clean_inventory.infrastructure.messaging import ConsoleLogger, InProcessEventPublisher
from clean_inventory.infrastructure.persistence import InMemoryProductRepository
from clean_inventory.shared.exceptions import ConflictError, NotFoundError, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(
    sku: str = "WIDGET-001",
    name: str = "Test Widget",
    price: str = "9.99",
    stock: int = 100,
    reorder: int = 10,
) -> Product:
    return Product.create(
        sku=sku,
        name=name,
        price_amount=price,
        initial_stock=stock,
        reorder_threshold=reorder,
    )


def _null_publisher() -> AbstractEventPublisher:
    pub = MagicMock(spec=AbstractEventPublisher)
    return pub


def _null_logger() -> AbstractLogger:
    log = MagicMock(spec=AbstractLogger)
    return log


# ===========================================================================
# VALUE OBJECTS
# ===========================================================================


class TestMoney(unittest.TestCase):
    def test_valid_money(self):
        m = Money.of("9.99")
        self.assertEqual(m.amount, Decimal("9.99"))
        self.assertEqual(m.currency, "USD")

    def test_negative_amount_raises(self):
        with self.assertRaises(ValidationError):
            Money.of("-1.00")

    def test_add_same_currency(self):
        a = Money.of("10.00")
        b = Money.of("5.50")
        self.assertEqual(a.add(b).amount, Decimal("15.50"))

    def test_add_different_currency_raises(self):
        a = Money.of("10.00", "USD")
        b = Money.of("10.00", "EUR")
        with self.assertRaises(ValidationError):
            a.add(b)

    def test_subtract_valid(self):
        a = Money.of("10.00")
        b = Money.of("3.00")
        self.assertEqual(a.subtract(b).amount, Decimal("7.00"))

    def test_subtract_overdraft_raises(self):
        a = Money.of("5.00")
        b = Money.of("10.00")
        with self.assertRaises(ValidationError):
            a.subtract(b)

    def test_multiply(self):
        m = Money.of("4.00")
        self.assertEqual(m.multiply(3).amount, Decimal("12.00"))

    def test_invalid_currency_raises(self):
        with self.assertRaises(ValidationError):
            Money(amount=Decimal("1"), currency="INVALID")


class TestQuantity(unittest.TestCase):
    def test_zero(self):
        q = Quantity.zero()
        self.assertTrue(q.is_zero())

    def test_negative_raises(self):
        with self.assertRaises(ValidationError):
            Quantity(-1)

    def test_add(self):
        self.assertEqual(Quantity(5).add(Quantity(3)).value, 8)

    def test_subtract_valid(self):
        self.assertEqual(Quantity(10).subtract(Quantity(4)).value, 6)

    def test_subtract_overdraft_raises(self):
        with self.assertRaises(ValidationError):
            Quantity(2).subtract(Quantity(5))


class TestSKU(unittest.TestCase):
    def test_normalised_to_uppercase(self):
        self.assertEqual(SKU("widget-001").code, "WIDGET-001")

    def test_blank_raises(self):
        with self.assertRaises(ValidationError):
            SKU("   ")

    def test_too_long_raises(self):
        with self.assertRaises(ValidationError):
            SKU("X" * 65)


class TestReorderThreshold(unittest.TestCase):
    def test_breached_when_at_threshold(self):
        t = ReorderThreshold(10)
        self.assertTrue(t.is_breached_by(Quantity(10)))

    def test_breached_when_below_threshold(self):
        t = ReorderThreshold(10)
        self.assertTrue(t.is_breached_by(Quantity(5)))

    def test_not_breached_when_above_threshold(self):
        t = ReorderThreshold(10)
        self.assertFalse(t.is_breached_by(Quantity(11)))


# ===========================================================================
# DOMAIN ENTITY
# ===========================================================================


class TestProductAggregate(unittest.TestCase):
    def test_create_emits_product_created_event(self):
        p = _make_product()
        events = p.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], ProductCreated)

    def test_add_stock_increases_quantity(self):
        p = _make_product(stock=50)
        p.pull_events()  # drain creation event
        p.add_stock(20)
        self.assertEqual(p.stock.value, 70)
        events = p.pull_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], StockAdded)

    def test_reduce_stock_decreases_quantity(self):
        p = _make_product(stock=50)
        p.pull_events()
        p.reduce_stock(10)
        self.assertEqual(p.stock.value, 40)
        events = p.pull_events()
        self.assertIsInstance(events[0], StockReduced)

    def test_reduce_below_threshold_emits_reorder_alert(self):
        p = _make_product(stock=11, reorder=10)
        p.pull_events()
        p.reduce_stock(2)  # now at 9, below threshold of 10
        events = p.pull_events()
        event_types = {type(e) for e in events}
        self.assertIn(ReorderAlertTriggered, event_types)

    def test_reduce_stock_overdraft_raises(self):
        p = _make_product(stock=5)
        with self.assertRaises(ValidationError):
            p.reduce_stock(10)

    def test_deactivate_prevents_further_mutations(self):
        p = _make_product()
        p.pull_events()
        p.deactivate()
        with self.assertRaises(ConflictError):
            p.add_stock(1)

    def test_double_deactivation_raises(self):
        p = _make_product()
        p.deactivate()
        with self.assertRaises(ConflictError):
            p.deactivate()

    def test_update_price(self):
        p = _make_product(price="5.00")
        p.pull_events()
        p.update_price("12.00")
        self.assertEqual(p.price.amount, Decimal("12.00"))

    def test_pull_events_clears_list(self):
        p = _make_product()
        p.pull_events()
        self.assertEqual(p.pull_events(), [])


# ===========================================================================
# INFRASTRUCTURE — Repository
# ===========================================================================


class TestInMemoryProductRepository(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        self.product = _make_product()
        self.repo.save(self.product)

    def test_find_by_id(self):
        found = self.repo.find_by_id(self.product.id)
        self.assertIsNotNone(found)

    def test_find_by_id_missing(self):
        self.assertIsNone(self.repo.find_by_id(uuid4()))

    def test_find_by_sku(self):
        found = self.repo.find_by_sku(SKU("WIDGET-001"))
        self.assertIsNotNone(found)

    def test_find_all_active(self):
        inactive = _make_product(sku="INACTIVE-001")
        inactive.deactivate()
        inactive.pull_events()
        self.repo.save(inactive)
        active = self.repo.find_all_active()
        skus = {p.sku.code for p in active}
        self.assertIn("WIDGET-001", skus)
        self.assertNotIn("INACTIVE-001", skus)

    def test_find_below_reorder_threshold(self):
        low = _make_product(sku="LOW-001", stock=2, reorder=10)
        low.pull_events()
        self.repo.save(low)
        candidates = self.repo.find_below_reorder_threshold()
        self.assertTrue(any(p.sku.code == "LOW-001" for p in candidates))

    def test_delete(self):
        self.repo.delete(self.product.id)
        self.assertIsNone(self.repo.find_by_id(self.product.id))


# ===========================================================================
# INFRASTRUCTURE — Event Publisher
# ===========================================================================


class TestInProcessEventPublisher(unittest.TestCase):
    def test_handler_called_on_matching_event(self):
        pub = InProcessEventPublisher()
        received: List = []
        pub.register(ProductCreated, received.append)

        product = _make_product()
        events = product.pull_events()
        pub.publish_all(events)

        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], ProductCreated)

    def test_unregistered_event_type_ignored(self):
        pub = InProcessEventPublisher()
        received: List = []
        pub.register(StockAdded, received.append)

        product = _make_product()
        pub.publish_all(product.pull_events())  # only ProductCreated

        self.assertEqual(len(received), 0)


# ===========================================================================
# APPLICATION — Use Cases
# ===========================================================================


class TestCreateProductUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        self.uc = CreateProductUseCase(self.repo, _null_publisher(), _null_logger())

    def test_creates_and_returns_product(self):
        cmd = CreateProductCommand(sku="SKU-A", name="Alpha", price_amount="1.00")
        result = self.uc.execute(cmd)
        self.assertEqual(result.sku, "SKU-A")

    def test_duplicate_sku_raises_conflict(self):
        cmd = CreateProductCommand(sku="SKU-A", name="Alpha", price_amount="1.00")
        self.uc.execute(cmd)
        with self.assertRaises(ConflictError):
            self.uc.execute(cmd)


class TestGetProductUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        product = _make_product()
        product.pull_events()
        self.repo.save(product)
        self.product_id = product.id
        self.uc = GetProductUseCase(self.repo)

    def test_returns_product(self):
        result = self.uc.execute(GetProductQuery(self.product_id))
        self.assertEqual(result.id, self.product_id)

    def test_missing_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.uc.execute(GetProductQuery(uuid4()))


class TestAddStockUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        product = _make_product(stock=10)
        product.pull_events()
        self.repo.save(product)
        self.product_id = product.id
        self.uc = AddStockUseCase(self.repo, _null_publisher(), _null_logger())

    def test_increases_stock(self):
        result = self.uc.execute(AddStockCommand(self.product_id, 5))
        self.assertEqual(result.stock, 15)


class TestReduceStockUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        product = _make_product(stock=20)
        product.pull_events()
        self.repo.save(product)
        self.product_id = product.id
        self.uc = ReduceStockUseCase(self.repo, _null_publisher(), _null_logger())

    def test_decreases_stock(self):
        result = self.uc.execute(ReduceStockCommand(self.product_id, 7))
        self.assertEqual(result.stock, 13)


class TestUpdatePriceUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        product = _make_product(price="5.00")
        product.pull_events()
        self.repo.save(product)
        self.product_id = product.id
        self.uc = UpdatePriceUseCase(self.repo, _null_publisher(), _null_logger())

    def test_updates_price(self):
        result = self.uc.execute(UpdatePriceCommand(self.product_id, "99.99"))
        self.assertEqual(result.price_amount, Decimal("99.99"))


class TestDeactivateProductUseCase(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryProductRepository()
        product = _make_product()
        product.pull_events()
        self.repo.save(product)
        self.product_id = product.id
        self.uc = DeactivateProductUseCase(self.repo, _null_publisher(), _null_logger())

    def test_deactivates_product(self):
        result = self.uc.execute(DeactivateProductCommand(self.product_id))
        self.assertFalse(result.is_active)


class TestListActiveProductsUseCase(unittest.TestCase):
    def test_excludes_inactive(self):
        repo = InMemoryProductRepository()
        active = _make_product(sku="ACTIVE-001")
        inactive = _make_product(sku="GONE-001")
        inactive.deactivate()
        active.pull_events()
        inactive.pull_events()
        repo.save(active)
        repo.save(inactive)

        uc = ListActiveProductsUseCase(repo)
        results = uc.execute()
        skus = {r.sku for r in results}
        self.assertIn("ACTIVE-001", skus)
        self.assertNotIn("GONE-001", skus)


class TestGetReorderCandidatesUseCase(unittest.TestCase):
    def test_returns_low_stock_products(self):
        repo = InMemoryProductRepository()
        low = _make_product(sku="LOW-001", stock=3, reorder=10)
        ok = _make_product(sku="OK-001", stock=50, reorder=10)
        low.pull_events()
        ok.pull_events()
        repo.save(low)
        repo.save(ok)

        uc = GetReorderCandidatesUseCase(repo)
        results = uc.execute()
        skus = {r.sku for r in results}
        self.assertIn("LOW-001", skus)
        self.assertNotIn("OK-001", skus)


# ===========================================================================
# INTEGRATION — Full Container Wiring
# ===========================================================================


class TestContainerIntegration(unittest.TestCase):
    def setUp(self):
        self.container = Container()

    def test_full_happy_path(self):
        # Create
        resp = self.container.create_product.execute(
            CreateProductCommand(sku="INT-001", name="Integration Widget", price_amount="25.00",
                                 initial_stock=50, reorder_threshold=5)
        )
        pid = resp.id
        self.assertEqual(resp.stock, 50)

        # Add stock
        resp = self.container.add_stock.execute(AddStockCommand(pid, 10))
        self.assertEqual(resp.stock, 60)

        # Reduce stock
        resp = self.container.reduce_stock.execute(ReduceStockCommand(pid, 5))
        self.assertEqual(resp.stock, 55)

        # Update price
        resp = self.container.update_price.execute(UpdatePriceCommand(pid, "30.00"))
        self.assertEqual(resp.price_amount, Decimal("30.00"))

        # List active
        products = self.container.list_active_products.execute()
        self.assertTrue(any(p.id == pid for p in products))

        # Deactivate
        resp = self.container.deactivate_product.execute(DeactivateProductCommand(pid))
        self.assertFalse(resp.is_active)

        # No longer in active list
        products = self.container.list_active_products.execute()
        self.assertFalse(any(p.id == pid for p in products))

    def test_swappable_repository(self):
        """Verify that a different repository can be injected without touching use cases."""
        custom_repo = InMemoryProductRepository()
        container = Container(repository=custom_repo)
        container.create_product.execute(
            CreateProductCommand(sku="SWAP-001", name="Swap Test", price_amount="1.00")
        )
        self.assertEqual(custom_repo.count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
