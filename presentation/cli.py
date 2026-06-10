"""
Presentation — Command-Line Interface.

The CLI layer translates user input into DTOs and delegates to use cases.
It knows nothing about the domain model or infrastructure.
Single Responsibility: I/O formatting and argument parsing only.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from uuid import UUID

from clean_inventory.application.dtos import (
    AddStockCommand,
    CreateProductCommand,
    DeactivateProductCommand,
    GetProductQuery,
    ReduceStockCommand,
    UpdatePriceCommand,
)
from clean_inventory.infrastructure.container import Container
from clean_inventory.shared.exceptions import DomainError, NotFoundError


def _print_product(data) -> None:
    """Pretty-print a ProductResponse as JSON."""
    print(
        json.dumps(
            {
                "id": str(data.id),
                "sku": data.sku,
                "name": data.name,
                "price": f"{data.currency} {data.price_amount:.2f}",
                "stock": data.stock,
                "reorder_threshold": data.reorder_threshold,
                "is_active": data.is_active,
                "created_at": data.created_at.isoformat(),
                "updated_at": data.updated_at.isoformat(),
            },
            indent=2,
        )
    )


class InventoryCLI:
    """
    CLI entry point.

    Open/Closed: add new sub-commands without modifying existing command handlers.
    """

    def __init__(self, container: Container) -> None:
        self._container = container
        self._parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> int:
        args = self._parser.parse_args(argv)
        if not hasattr(args, "func"):
            self._parser.print_help()
            return 0
        try:
            args.func(args)
            return 0
        except (DomainError, NotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # ------------------------------------------------------------------
    # Parser builder — Open/Closed: each sub-command is self-contained
    # ------------------------------------------------------------------

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="inventory",
            description="Clean Architecture Inventory Management CLI",
        )
        sub = parser.add_subparsers(title="commands")
        self._add_create_command(sub)
        self._add_get_command(sub)
        self._add_list_command(sub)
        self._add_add_stock_command(sub)
        self._add_reduce_stock_command(sub)
        self._add_update_price_command(sub)
        self._add_deactivate_command(sub)
        self._add_reorder_command(sub)
        return parser

    def _add_create_command(self, sub) -> None:
        p = sub.add_parser("create", help="Create a new product")
        p.add_argument("sku")
        p.add_argument("name")
        p.add_argument("price")
        p.add_argument("--currency", default="USD")
        p.add_argument("--stock", type=int, default=0)
        p.add_argument("--reorder", type=int, default=0)
        p.set_defaults(func=self._handle_create)

    def _add_get_command(self, sub) -> None:
        p = sub.add_parser("get", help="Get a product by ID")
        p.add_argument("product_id", type=UUID)
        p.set_defaults(func=self._handle_get)

    def _add_list_command(self, sub) -> None:
        p = sub.add_parser("list", help="List all active products")
        p.set_defaults(func=self._handle_list)

    def _add_add_stock_command(self, sub) -> None:
        p = sub.add_parser("add-stock", help="Add stock to a product")
        p.add_argument("product_id", type=UUID)
        p.add_argument("quantity", type=int)
        p.set_defaults(func=self._handle_add_stock)

    def _add_reduce_stock_command(self, sub) -> None:
        p = sub.add_parser("reduce-stock", help="Reduce stock of a product")
        p.add_argument("product_id", type=UUID)
        p.add_argument("quantity", type=int)
        p.set_defaults(func=self._handle_reduce_stock)

    def _add_update_price_command(self, sub) -> None:
        p = sub.add_parser("update-price", help="Update the price of a product")
        p.add_argument("product_id", type=UUID)
        p.add_argument("new_price")
        p.add_argument("--currency")
        p.set_defaults(func=self._handle_update_price)

    def _add_deactivate_command(self, sub) -> None:
        p = sub.add_parser("deactivate", help="Deactivate a product")
        p.add_argument("product_id", type=UUID)
        p.add_argument("--reason", default="")
        p.set_defaults(func=self._handle_deactivate)

    def _add_reorder_command(self, sub) -> None:
        p = sub.add_parser("reorder", help="List products below reorder threshold")
        p.set_defaults(func=self._handle_reorder)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _handle_create(self, args) -> None:
        cmd = CreateProductCommand(
            sku=args.sku,
            name=args.name,
            price_amount=args.price,
            currency=args.currency,
            initial_stock=args.stock,
            reorder_threshold=args.reorder,
        )
        result = self._container.create_product.execute(cmd)
        _print_product(result)

    def _handle_get(self, args) -> None:
        result = self._container.get_product.execute(GetProductQuery(args.product_id))
        _print_product(result)

    def _handle_list(self, args) -> None:
        products = self._container.list_active_products.execute()
        for product in products:
            _print_product(product)

    def _handle_add_stock(self, args) -> None:
        cmd = AddStockCommand(product_id=args.product_id, quantity=args.quantity)
        result = self._container.add_stock.execute(cmd)
        _print_product(result)

    def _handle_reduce_stock(self, args) -> None:
        cmd = ReduceStockCommand(product_id=args.product_id, quantity=args.quantity)
        result = self._container.reduce_stock.execute(cmd)
        _print_product(result)

    def _handle_update_price(self, args) -> None:
        cmd = UpdatePriceCommand(
            product_id=args.product_id,
            new_amount=args.new_price,
            currency=args.currency,
        )
        result = self._container.update_price.execute(cmd)
        _print_product(result)

    def _handle_deactivate(self, args) -> None:
        cmd = DeactivateProductCommand(product_id=args.product_id, reason=args.reason)
        result = self._container.deactivate_product.execute(cmd)
        _print_product(result)

    def _handle_reorder(self, args) -> None:
        products = self._container.get_reorder_candidates.execute()
        if not products:
            print("No products below reorder threshold.")
            return
        for product in products:
            _print_product(product)


def main() -> None:
    container = Container()
    cli = InventoryCLI(container)
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
