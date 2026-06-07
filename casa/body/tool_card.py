#!/usr/bin/env python3
"""Tool catalog cards → mm_event for auto-ingest (ADR-0046)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from casa.body.contracts import FunctionSpec

ChangeKind = Literal["added", "changed", "removed"]


@dataclass(frozen=True)
class ToolCard:
    function_id: str
    title: str
    description: str
    slot_summary: tuple[dict[str, str], ...]
    function_family: str
    server_id: str
    wire_kind: str


def schema_slot_summary(input_schema: dict[str, Any]) -> tuple[dict[str, str], ...]:
    props = input_schema.get("properties") if isinstance(input_schema.get("properties"), dict) else {}
    out: list[dict[str, str]] = []
    for name, meta in sorted(props.items()):
        if not isinstance(meta, dict):
            out.append({"name": str(name), "type": "unknown"})
            continue
        out.append({"name": str(name), "type": str(meta.get("type") or "unknown")})
    return tuple(out)


def infer_function_family(function_id: str, wire: dict[str, Any]) -> str:
    parts = function_id.split(".")
    if len(parts) >= 2:
        return parts[1]
    tool = str(wire.get("tool") or "")
    if tool.startswith("ide_git"):
        return "git"
    if "build" in tool or "verify" in tool:
        return "build"
    if "notes" in tool:
        return "notes"
    return parts[0] if parts else "tool"


def infer_server_id(wire: dict[str, Any]) -> str:
    return str(wire.get("server") or wire.get("kind") or "unknown")


def tool_card_from_spec(spec: FunctionSpec) -> ToolCard:
    wire = spec.wire or {}
    return ToolCard(
        function_id=spec.function_id,
        title=spec.title,
        description=spec.description,
        slot_summary=schema_slot_summary(spec.input_schema),
        function_family=infer_function_family(spec.function_id, wire),
        server_id=infer_server_id(wire),
        wire_kind=str(wire.get("kind") or spec.backend_id),
    )


def _description_words(text: str, *, limit: int = 32) -> list[str]:
    return [w for w in text.replace("/", " ").split() if w][:limit]


def tool_card_to_mm_event(
    spec: FunctionSpec,
    *,
    change_kind: ChangeKind = "added",
    window_ms: int = 0,
) -> dict[str, Any]:
    card = tool_card_from_spec(spec)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title_words = _description_words(card.title, limit=8)
    desc_words = _description_words(card.description)
    words = list(dict.fromkeys(title_words + desc_words))[:40]
    slot_names = [s["name"] for s in card.slot_summary]
    tags = [
        "body:tool_catalog",
        f"change:{change_kind}",
        f"fn:{card.function_id}",
        f"family:{card.function_family}",
        f"tool:server:{card.server_id}",
    ]
    return {
        "schema": "mm_event_v1",
        "at": ts,
        "window_ms": window_ms,
        "source": "body_catalog_ingest",
        "canon": {
            "words": words,
            "context": tags,
        },
        "body": {
            "kind": "tool_catalog",
            "change_kind": change_kind,
            "function_id": card.function_id,
            "title": card.title,
            "description": card.description,
            "function_family": card.function_family,
            "server_id": card.server_id,
            "wire_kind": card.wire_kind,
            "slot_summary": [dict(s) for s in card.slot_summary],
            "slot_names": slot_names,
        },
    }


def tool_removed_to_mm_event(function_id: str, *, window_ms: int = 0) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    family = infer_function_family(function_id, {})
    return {
        "schema": "mm_event_v1",
        "at": ts,
        "window_ms": window_ms,
        "source": "body_catalog_ingest",
        "canon": {
            "words": [function_id, "removed"],
            "context": ["body:tool_catalog", "change:removed", f"fn:{function_id}", f"family:{family}"],
        },
        "body": {
            "kind": "tool_catalog",
            "change_kind": "removed",
            "function_id": function_id,
            "function_family": family,
        },
    }
