#!/usr/bin/env python3
"""Backend factory from body_manifest backends section."""

from __future__ import annotations

from typing import Any

from pathlib import Path

from casa.body.backends.stub import StubFunctionBackend
from casa.body.contracts import FunctionCallBackend


def build_backend(backend_id: str, config: dict[str, Any] | None = None) -> FunctionCallBackend:
    cfg = config or {}
    if backend_id == "stub":
        handlers = cfg.get("handlers")
        if isinstance(handlers, dict):
            return StubFunctionBackend(handlers=handlers)
        return StubFunctionBackend()
    if backend_id == "mcp":
        raise NotImplementedError(
            "mcp backend: host must inject transport (Cursor stdio, CIDE loopback). See ADR-0046."
        )
    if backend_id == "ide_command":
        raise NotImplementedError(
            "ide_command backend: wire via CIDE agent-contract or in-process IIdeMcpActions. See ADR-0046."
        )
    if backend_id == "in_process":
        from casa.body.backends.in_process import InProcessFunctionBackend

        store_dir = cfg.get("store_dir")
        return InProcessFunctionBackend(
            store_dir=Path(store_dir).resolve() if store_dir else None,
        )
    raise KeyError(f"unknown function backend: {backend_id}")
