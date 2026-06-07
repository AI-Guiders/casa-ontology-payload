#!/usr/bin/env python3
"""MCP/catalog sync — digest, diff, manifest merge (ADR-0046)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from casa.body.contracts import FunctionSpec
from casa.body.extension import parse_function_spec, specs_from_manifest


def _digest_entry(spec: FunctionSpec) -> dict[str, Any]:
    from casa.body.tool_card import schema_slot_summary

    wire = spec.wire or {}
    return {
        "function_id": spec.function_id,
        "title": spec.title,
        "description": spec.description,
        "backend_id": spec.backend_id,
        "slots": [dict(s) for s in schema_slot_summary(spec.input_schema)],
        "wire_kind": str(wire.get("kind") or ""),
        "wire_tool": str(wire.get("tool") or wire.get("command_id") or ""),
        "wire_server": str(wire.get("server") or ""),
    }


def catalog_digest(specs: dict[str, FunctionSpec]) -> str:
    entries = [_digest_entry(specs[k]) for k in sorted(specs)]
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CatalogDiff:
    added: tuple[FunctionSpec, ...] = ()
    changed: tuple[FunctionSpec, ...] = ()
    removed: tuple[str, ...] = ()
    old_digest: str = ""
    new_digest: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)


@dataclass
class CatalogSyncResult:
    diff: CatalogDiff
    manifest: dict[str, Any]
    skipped: bool = False


def diff_catalog(
    old_specs: dict[str, FunctionSpec],
    new_specs: dict[str, FunctionSpec],
    *,
    old_digest: str = "",
) -> CatalogDiff:
    old_digest = old_digest or catalog_digest(old_specs)
    new_digest = catalog_digest(new_specs)
    if old_digest == new_digest:
        return CatalogDiff(old_digest=old_digest, new_digest=new_digest)

    old_ids = set(old_specs)
    new_ids = set(new_specs)
    added = tuple(new_specs[fid] for fid in sorted(new_ids - old_ids))
    removed = tuple(sorted(old_ids - new_ids))

    changed: list[FunctionSpec] = []
    for fid in sorted(old_ids & new_ids):
        if _digest_entry(old_specs[fid]) != _digest_entry(new_specs[fid]):
            changed.append(new_specs[fid])

    return CatalogDiff(
        added=added,
        changed=tuple(changed),
        removed=removed,
        old_digest=old_digest,
        new_digest=new_digest,
    )


def spec_to_manifest_row(spec: FunctionSpec) -> dict[str, Any]:
    return {
        "function_id": spec.function_id,
        "title": spec.title,
        "description": spec.description,
        "input_schema": spec.input_schema,
        "backend_id": spec.backend_id,
        "wire": dict(spec.wire or {}),
    }


def merge_manifest_functions(manifest: dict[str, Any], specs: dict[str, FunctionSpec]) -> dict[str, Any]:
    merged = dict(manifest)
    merged["functions"] = [spec_to_manifest_row(specs[k]) for k in sorted(specs)]
    merged["catalog_digest"] = catalog_digest(specs)
    merged["catalog_function_count"] = len(specs)
    return merged


def specs_from_mcp_tools(
    tools: list[dict[str, Any]],
    *,
    server_id: str,
    backend_id: str = "mcp",
    id_prefix: str = "tool",
) -> dict[str, FunctionSpec]:
    """Normalize MCP tools/list entries to FunctionSpec map."""
    out: dict[str, FunctionSpec] = {}
    for raw in tools:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        safe = name.replace("-", "_")
        function_id = f"{id_prefix}.{server_id}.{safe}" if id_prefix else safe
        schema = raw.get("inputSchema") if isinstance(raw.get("inputSchema"), dict) else {}
        if not schema and isinstance(raw.get("input_schema"), dict):
            schema = raw["input_schema"]
        out[function_id] = FunctionSpec(
            function_id=function_id,
            title=name,
            description=str(raw.get("description") or ""),
            input_schema=schema or {"type": "object", "properties": {}},
            backend_id=backend_id,
            wire={"kind": "mcp", "server": server_id, "tool": name},
        )
    return out


def sync_catalog(
    manifest: dict[str, Any],
    incoming: dict[str, FunctionSpec],
    *,
    last_digest: str | None = None,
) -> CatalogSyncResult:
    old_specs = specs_from_manifest(manifest)
    digest_hint = last_digest if last_digest is not None else str(manifest.get("catalog_digest") or "")
    diff = diff_catalog(old_specs, incoming, old_digest=digest_hint if digest_hint else catalog_digest(old_specs))

    if not diff.has_changes and digest_hint and digest_hint == diff.new_digest:
        return CatalogSyncResult(diff=diff, manifest=manifest, skipped=True)

    merged = merge_manifest_functions(manifest, incoming)
    return CatalogSyncResult(diff=diff, manifest=merged, skipped=not diff.has_changes)


def parse_incoming_specs(items: list[dict[str, Any]]) -> dict[str, FunctionSpec]:
    out: dict[str, FunctionSpec] = {}
    for item in items:
        if isinstance(item, dict) and item.get("function_id"):
            spec = parse_function_spec(item)
            out[spec.function_id] = spec
    return out
