"""
Domain-specific exceptions.
Defined in shared so all layers can reference them without circular imports.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base for all domain rule violations."""


class NotFoundError(DomainError):
    """Raised when a requested aggregate/entity does not exist."""


class ValidationError(DomainError):
    """Raised when a value object or entity invariant is violated."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state."""


class InfrastructureError(Exception):
    """Base for all infrastructure-layer failures."""


class PersistenceError(InfrastructureError):
    """Raised when the persistence layer cannot complete an operation."""


class MessagingError(InfrastructureError):
    """Raised when the messaging layer cannot deliver an event."""
