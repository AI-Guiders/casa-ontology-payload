#!/usr/bin/env python3
"""Client-agnostic function calling contracts (ADR-0046)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class FunctionSpec:
    """Catalog entry — independent of MCP / IDE / CLI wire."""

    function_id: str
    title: str
    description: str
    input_schema: dict[str, Any]
    backend_id: str
    wire: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FunctionCallIntent:
    """Motor intent from brain or host relay (not raw JSON-RPC)."""

    function_id: str
    arguments: dict[str, Any]
    call_id: str
    provenance: dict[str, Any] = field(default_factory=dict)
    disposition: str | None = None  # accept | defer | refuse


@dataclass(frozen=True)
class FunctionCallResult:
    """Normalized tool outcome for mm_event / dialogue / journal."""

    call_id: str
    function_id: str
    ok: bool
    summary: str
    structured: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    is_transient: bool = False
    wire_backend: str = ""
    duration_ms: int = 0


@runtime_checkable
class FunctionCallBackend(Protocol):
    backend_id: str

    def execute(self, spec: FunctionSpec, arguments: dict[str, Any]) -> FunctionCallResult: ...

    def health(self) -> dict[str, Any]: ...
