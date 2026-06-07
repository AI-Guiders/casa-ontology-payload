#!/usr/bin/env python3
"""Body function extension point — dispatch intents to wire backends (ADR-0046)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from casa.body.backends.registry import build_backend
from casa.body.contracts import (
    FunctionCallBackend,
    FunctionCallIntent,
    FunctionCallResult,
    FunctionSpec,
)


def body_manifest_path(store_dir: Path) -> Path:
    return store_dir.resolve() / "body_manifest.json"


def load_body_manifest(store_dir: Path) -> dict[str, Any]:
    path = body_manifest_path(store_dir)
    if not path.is_file():
        return {
            "schema_version": 1,
            "body_profile_id": "default",
            "default_backend": "stub",
            "functions": [],
            "backends": {"stub": {}},
        }
    return json.loads(path.read_text(encoding="utf-8"))


def parse_function_spec(raw: dict[str, Any]) -> FunctionSpec:
    return FunctionSpec(
        function_id=str(raw.get("function_id") or ""),
        title=str(raw.get("title") or raw.get("function_id") or ""),
        description=str(raw.get("description") or ""),
        input_schema=raw.get("input_schema") if isinstance(raw.get("input_schema"), dict) else {"type": "object", "properties": {}},
        backend_id=str(raw.get("backend_id") or "stub"),
        wire=raw.get("wire") if isinstance(raw.get("wire"), dict) else {},
    )


_parse_spec = parse_function_spec


def specs_from_manifest(manifest: dict[str, Any]) -> dict[str, FunctionSpec]:
    out: dict[str, FunctionSpec] = {}
    for item in manifest.get("functions") or []:
        if isinstance(item, dict) and item.get("function_id"):
            spec = parse_function_spec(item)
            out[spec.function_id] = spec
    return out


class BodyFunctionExtension:
    """Client-agnostic function calling — catalog + dispatch."""

    def __init__(
        self,
        store_dir: Path,
        *,
        manifest: dict[str, Any] | None = None,
        backends: dict[str, FunctionCallBackend] | None = None,
    ) -> None:
        self.store_dir = store_dir.resolve()
        self.manifest = manifest if manifest is not None else load_body_manifest(self.store_dir)
        self._specs: dict[str, FunctionSpec] = {}
        for item in self.manifest.get("functions") or []:
            if isinstance(item, dict) and item.get("function_id"):
                spec = parse_function_spec(item)
                self._specs[spec.function_id] = spec
        self._backends: dict[str, FunctionCallBackend] = dict(backends or {})
        self._ensure_backends()

    def _ensure_backends(self) -> None:
        backend_cfgs = self.manifest.get("backends")
        if not isinstance(backend_cfgs, dict):
            backend_cfgs = {}
        needed = {spec.backend_id for spec in self._specs.values()}
        needed.add(str(self.manifest.get("default_backend") or "stub"))
        for bid in needed:
            if bid in self._backends:
                continue
            cfg = dict(backend_cfgs.get(bid) if isinstance(backend_cfgs.get(bid), dict) else {})
            if bid == "in_process" and "store_dir" not in cfg:
                cfg["store_dir"] = str(self.store_dir)
            self._backends[bid] = build_backend(bid, cfg)

    def list_functions(self) -> list[FunctionSpec]:
        return list(self._specs.values())

    def get_spec(self, function_id: str) -> FunctionSpec | None:
        return self._specs.get(function_id)

    def health(self) -> dict[str, Any]:
        backends = {bid: be.health() for bid, be in self._backends.items()}
        ok = all(bool(h.get("ok", True)) for h in backends.values())
        return {
            "panel": "body.functions",
            "ok": ok,
            "body_profile_id": self.manifest.get("body_profile_id"),
            "function_count": len(self._specs),
            "backends": backends,
        }

    def dispatch(self, intent: FunctionCallIntent) -> FunctionCallResult:
        if intent.disposition in ("defer", "refuse"):
            return FunctionCallResult(
                call_id=intent.call_id or _new_call_id(),
                function_id=intent.function_id,
                ok=False,
                summary=f"not executed: subject {intent.disposition}",
                error_code=f"subject_{intent.disposition}",
                wire_backend="none",
            )

        spec = self._specs.get(intent.function_id)
        if spec is None:
            return FunctionCallResult(
                call_id=intent.call_id or _new_call_id(),
                function_id=intent.function_id,
                ok=False,
                summary=f"unknown function_id: {intent.function_id}",
                error_code="unknown_function",
                wire_backend="none",
            )

        backend = self._backends.get(spec.backend_id)
        if backend is None:
            return FunctionCallResult(
                call_id=intent.call_id or _new_call_id(),
                function_id=intent.function_id,
                ok=False,
                summary=f"backend not loaded: {spec.backend_id}",
                error_code="backend_missing",
                wire_backend=spec.backend_id,
            )

        call_id = intent.call_id or _new_call_id()
        t0 = time.perf_counter()
        raw = backend.execute(spec, dict(intent.arguments))
        result = replace(raw, call_id=call_id, function_id=spec.function_id)
        if result.duration_ms <= 0:
            result = replace(result, duration_ms=int((time.perf_counter() - t0) * 1000))
        return result


def _new_call_id() -> str:
    return uuid.uuid4().hex[:16]
