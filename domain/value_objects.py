"""
Value Objects — immutable, self-validating domain primitives.

Each class encapsulates a single concept and enforces its own invariants.
No two value objects share responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from clean_inventory.shared.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Money:
    """Represents an amount of money in a specific currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValidationError("Money amount cannot be negative.")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(f"Invalid ISO-4217 currency code: '{self.currency}'.")

    @classmethod
    def of(cls, amount: str | float | Decimal, currency: str = "USD") -> "Money":
        try:
            return cls(amount=Decimal(str(amount)), currency=currency.upper())
        except InvalidOperation as exc:
            raise ValidationError(f"Cannot parse '{amount}' as a monetary amount.") from exc

    def add(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        result = self.amount - other.amount
        if result < Decimal("0"):
            raise ValidationError("Subtraction would yield a negative money amount.")
        return Money(amount=result, currency=self.currency)

    def multiply(self, factor: int | Decimal) -> "Money":
        return Money(amount=self.amount * Decimal(str(factor)), currency=self.currency)

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValidationError(
                f"Cannot operate on different currencies: "
                f"'{self.currency}' vs '{other.currency}'."
            )

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"


# ---------------------------------------------------------------------------
# Quantity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Quantity:
    """Represents a non-negative integer stock quantity."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise ValidationError("Quantity must be an integer.")
        if self.value < 0:
            raise ValidationError("Quantity cannot be negative.")

    @classmethod
    def zero(cls) -> "Quantity":
        return cls(value=0)

    def add(self, other: "Quantity") -> "Quantity":
        return Quantity(value=self.value + other.value)

    def subtract(self, other: "Quantity") -> "Quantity":
        result = self.value - other.value
        if result < 0:
            raise ValidationError(
                f"Cannot subtract {other.value} from {self.value}: result would be negative."
            )
        return Quantity(value=result)

    def is_zero(self) -> bool:
        return self.value == 0

    def __str__(self) -> str:
        return str(self.value)


# ---------------------------------------------------------------------------
# SKU
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SKU:
    """Stock Keeping Unit — a unique product identifier string."""

    code: str

    def __post_init__(self) -> None:
        cleaned = self.code.strip()
        if not cleaned:
            raise ValidationError("SKU code cannot be blank.")
        if len(cleaned) > 64:
            raise ValidationError("SKU code must not exceed 64 characters.")
        object.__setattr__(self, "code", cleaned.upper())

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# ProductName
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductName:
    """A validated, trimmed product display name."""

    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned:
            raise ValidationError("Product name cannot be blank.")
        if len(cleaned) > 255:
            raise ValidationError("Product name must not exceed 255 characters.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# ReorderThreshold
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReorderThreshold:
    """Minimum quantity at which a reorder alert should be triggered."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValidationError("Reorder threshold cannot be negative.")

    def is_breached_by(self, current: Quantity) -> bool:
        return current.value <= self.value
