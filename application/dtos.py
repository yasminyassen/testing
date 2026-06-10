"""
Data Transfer Objects (DTOs) — plain data structures for crossing layer boundaries.

DTOs carry no behaviour. They decouple the application interface from domain internals
and give each use case a typed, validated input/output contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


# ---------------------------------------------------------------------------
# Command DTOs  (inbound — callers → use cases)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreateProductCommand:
    sku: str
    name: str
    price_amount: str
    currency: str = "USD"
    initial_stock: int = 0
    reorder_threshold: int = 0


@dataclass(frozen=True)
class AddStockCommand:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class ReduceStockCommand:
    product_id: UUID
    quantity: int


@dataclass(frozen=True)
class UpdatePriceCommand:
    product_id: UUID
    new_amount: str
    currency: Optional[str] = None


@dataclass(frozen=True)
class TransferStockCommand:
    source_product_id: UUID
    destination_product_id: UUID
    quantity: int


@dataclass(frozen=True)
class DeactivateProductCommand:
    product_id: UUID
    reason: str = ""


# ---------------------------------------------------------------------------
# Query DTOs (inbound — callers → use cases)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GetProductQuery:
    product_id: UUID


@dataclass(frozen=True)
class GetProductBySkuQuery:
    sku: str


# ---------------------------------------------------------------------------
# Response DTOs  (outbound — use cases → callers)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductResponse:
    id: UUID
    sku: str
    name: str
    price_amount: Decimal
    currency: str
    stock: int
    reorder_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
