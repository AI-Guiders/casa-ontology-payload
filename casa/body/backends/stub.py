#!/usr/bin/env python3
"""Stub function backend — CI and lab without MCP/CIDE."""

from __future__ import annotations

import time
from typing import Any

from casa.body.contracts import FunctionCallBackend, FunctionCallResult, FunctionSpec


class StubFunctionBackend:
    backend_id = "stub"

    def __init__(self, *, handlers: dict[str, Any] | None = None) -> None:
        self._handlers = handlers or {}

    def execute(self, spec: FunctionSpec, arguments: dict[str, Any]) -> FunctionCallResult:
        t0 = time.perf_counter()
        handler = self._handlers.get(spec.function_id)
        if handler is None:
            wire_tool = (spec.wire or {}).get("tool") or spec.function_id
            return FunctionCallResult(
                call_id="",
                function_id=spec.function_id,
                ok=True,
                summary=f"stub ok: {wire_tool}",
                structured={"echo": arguments, "wire": spec.wire},
                wire_backend=self.backend_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        try:
            out = handler(spec, arguments)
        except Exception as exc:  # noqa: BLE001 — backend boundary
            return FunctionCallResult(
                call_id="",
                function_id=spec.function_id,
                ok=False,
                summary=str(exc),
                error_code="stub_handler_error",
                error_message=str(exc),
                wire_backend=self.backend_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        if isinstance(out, FunctionCallResult):
            return out
        if isinstance(out, dict):
            ok = bool(out.get("ok", True))
            return FunctionCallResult(
                call_id=str(out.get("call_id") or ""),
                function_id=spec.function_id,
                ok=ok,
                summary=str(out.get("summary") or ("ok" if ok else "error")),
                structured=out.get("structured") if isinstance(out.get("structured"), dict) else out,
                error_code=out.get("error_code"),
                error_message=out.get("error_message"),
                wire_backend=self.backend_id,
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        return FunctionCallResult(
            call_id="",
            function_id=spec.function_id,
            ok=True,
            summary=str(out),
            wire_backend=self.backend_id,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    def health(self) -> dict[str, Any]:
        return {"backend_id": self.backend_id, "ok": True, "handlers": len(self._handlers)}
