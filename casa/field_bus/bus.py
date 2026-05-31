"""Synchronous FieldBus v0 (in-process pub/sub)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
_handlers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)
_log: list[Any] = []


def subscribe(event_type: type[T], handler: Callable[[T], None]) -> None:
    _handlers[event_type].append(handler)  # type: ignore[arg-type]


def publish(event: Any) -> None:
    _log.append(event)
    for handler in _handlers[type(event)]:
        handler(event)


def drain_log() -> list[Any]:
    out = list(_log)
    _log.clear()
    return out


def clear_subscribers() -> None:
    _handlers.clear()
