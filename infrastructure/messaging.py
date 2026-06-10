"""
Infrastructure — Concrete implementations of application-layer abstractions.

EventPublisher: in-process synchronous dispatcher.
ConsoleLogger: structured logging to stdout.

Both are swappable: replace with KafkaEventPublisher, CloudWatchLogger, etc.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Callable, Dict, List, Type

from clean_inventory.application.interfaces import AbstractEventPublisher, AbstractLogger
from clean_inventory.domain.events import DomainEvent


# ---------------------------------------------------------------------------
# Event Publisher
# ---------------------------------------------------------------------------


class InProcessEventPublisher(AbstractEventPublisher):
    """
    Synchronous in-process event dispatcher.

    Handlers are registered per event type.
    Open/Closed: add handlers via register() — the dispatcher never changes.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], None]]] = {}

    def register(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Subscribe *handler* to events of *event_type*."""
        self._handlers.setdefault(event_type, []).append(handler)

    def publish_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            for handler in self._handlers.get(type(event), []):
                handler(event)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


class ConsoleLogger(AbstractLogger):
    """
    Structured JSON logger that writes to stdout.

    Single Responsibility: format and emit log lines only.
    """

    def __init__(self, service_name: str = "clean_inventory") -> None:
        self._service = service_name

    def info(self, message: str, **context) -> None:
        self._emit("INFO", message, **context)

    def warning(self, message: str, **context) -> None:
        self._emit("WARNING", message, **context)

    def error(self, message: str, **context) -> None:
        self._emit("ERROR", message, **context)

    def _emit(self, level: str, message: str, **context) -> None:
        record = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": level,
            "service": self._service,
            "message": message,
            **context,
        }
        print(json.dumps(record), file=sys.stdout)
