#!/usr/bin/env python3
"""In-process function backend — Python handlers on host hot path (ADR-0046)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from casa.body.contracts import FunctionCallBackend, FunctionCallResult, FunctionSpec
from casa.body.handlers.registry import resolve_handler

HandlerFn = Callable[[FunctionSpec, dict[str, Any], Path | None], FunctionCallResult]


class InProcessFunctionBackend:
    backend_id = "in_process"

    def __init__(self, *, store_dir: Path | None = None) -> None:
        self._store_dir = store_dir.resolve() if store_dir else None

    def execute(self, spec: FunctionSpec, arguments: dict[str, Any]) -> FunctionCallResult:
        t0 = time.perf_counter()
        handler_id = str((spec.wire or {}).get("handler") or spec.function_id)
        handler = resolve_handler(handler_id)
        if handler is None:
            return FunctionCallResult(
                call_id="",
                function_id=spec.function_id,
                ok=False,
                summary=f"no in_process handler: {handler_id}",
                error_code="handler_missing",
                wire_backend=self.backend_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        store_arg = arguments.get("store_dir")
        store_dir = Path(store_arg).resolve() if store_arg else self._store_dir
        try:
            return handler(spec, arguments, store_dir)
        except Exception as exc:  # noqa: BLE001 — backend boundary
            return FunctionCallResult(
                call_id="",
                function_id=spec.function_id,
                ok=False,
                summary=str(exc),
                error_code="in_process_handler_error",
                error_message=str(exc),
                wire_backend=self.backend_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

    def health(self) -> dict[str, Any]:
        from casa.body.handlers.registry import registered_handler_ids

        return {
            "backend_id": self.backend_id,
            "ok": True,
            "store_dir": str(self._store_dir) if self._store_dir else None,
            "handlers": registered_handler_ids(),
        }
