"""
Shared primitive types used across all layers.
No dependencies on any internal module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar, Generic, Optional
from uuid import UUID


T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Monadic result type — eliminates exception-based flow control."""

    value: Optional[T]
    error: Optional[str]
    success: bool

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(value=value, error=None, success=True)

    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        return cls(value=None, error=error, success=False)

    def unwrap(self) -> T:
        if not self.success:
            raise ValueError(f"Called unwrap on a failed Result: {self.error}")
        return self.value  # type: ignore[return-value]


EntityId = UUID
