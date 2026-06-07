#!/usr/bin/env python3
"""In-process handler registry for BodyFunctionExtension."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pathlib import Path

    from casa.body.contracts import FunctionCallResult, FunctionSpec

HandlerFn = Callable[["FunctionSpec", dict[str, Any], "Path | None"], "FunctionCallResult"]

_HANDLERS: dict[str, HandlerFn] = {}
_BUILTINS_LOADED = False


def register_handler(handler_id: str, fn: HandlerFn) -> None:
    _HANDLERS[str(handler_id)] = fn


def _ensure_builtin_handlers() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    from casa.body.handlers import canon_nca as _canon_nca  # noqa: F401 — register on import

    _BUILTINS_LOADED = True


def resolve_handler(handler_id: str) -> HandlerFn | None:
    _ensure_builtin_handlers()
    return _HANDLERS.get(str(handler_id))


def registered_handler_ids() -> list[str]:
    _ensure_builtin_handlers()
    return sorted(_HANDLERS)
