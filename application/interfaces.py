"""
Application-layer abstractions that infrastructure must satisfy.

Defined here so use cases can depend on them without touching infrastructure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from clean_inventory.domain.events import DomainEvent


class AbstractEventPublisher(ABC):
    """Delivers domain events to interested subscribers."""

    @abstractmethod
    def publish_all(self, events: List[DomainEvent]) -> None:
        """Publish every event in *events* in order."""


class AbstractUnitOfWork(ABC):
    """
    Transactional boundary.

    Concrete implementations wrap a DB session, an in-memory store, etc.
    Use cases never commit or roll back directly — they delegate to this contract.
    """

    @abstractmethod
    def __enter__(self) -> "AbstractUnitOfWork":
        ...

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        ...

    @abstractmethod
    def commit(self) -> None:
        """Flush all pending changes to the underlying store."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard all pending changes."""


class AbstractLogger(ABC):
    """Structured logging contract consumed by use cases."""

    @abstractmethod
    def info(self, message: str, **context) -> None:
        ...

    @abstractmethod
    def warning(self, message: str, **context) -> None:
        ...

    @abstractmethod
    def error(self, message: str, **context) -> None:
        ...
