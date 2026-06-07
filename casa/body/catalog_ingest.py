#!/usr/bin/env python3
"""Auto-ingest tool catalog diff → jsonl mm_events (ADR-0046)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.body.catalog_sync import CatalogDiff, CatalogSyncResult, sync_catalog
from casa.body.contracts import FunctionSpec
from casa.body.extension import body_manifest_path, load_body_manifest
from casa.body.tool_card import tool_card_to_mm_event, tool_removed_to_mm_event


def tool_catalog_jsonl_path(store_dir: Path) -> Path:
    return store_dir.resolve() / "tool_catalog.live.jsonl"


def events_from_diff(diff: CatalogDiff) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for spec in diff.added:
        events.append(tool_card_to_mm_event(spec, change_kind="added"))
    for spec in diff.changed:
        events.append(tool_card_to_mm_event(spec, change_kind="changed"))
    for function_id in diff.removed:
        events.append(tool_removed_to_mm_event(function_id))
    return events


def append_events_jsonl(path: Path, events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(events)


@dataclass
class CatalogIngestReport:
    ok: bool
    skipped: bool
    event_count: int
    added: int
    changed: int
    removed: int
    old_digest: str
    new_digest: str
    jsonl_path: str
    manifest_path: str
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skipped": self.skipped,
            "event_count": self.event_count,
            "added": self.added,
            "changed": self.changed,
            "removed": self.removed,
            "old_digest": self.old_digest,
            "new_digest": self.new_digest,
            "jsonl_path": self.jsonl_path,
            "manifest_path": self.manifest_path,
        }


def run_catalog_auto_ingest(
    store_dir: Path,
    incoming: dict[str, FunctionSpec],
    *,
    last_digest: str | None = None,
    persist_manifest: bool = True,
    append_jsonl: bool = True,
) -> CatalogIngestReport:
    store_dir = store_dir.resolve()
    manifest = load_body_manifest(store_dir)
    sync: CatalogSyncResult = sync_catalog(manifest, incoming, last_digest=last_digest)
    events = events_from_diff(sync.diff)
    jsonl = tool_catalog_jsonl_path(store_dir)
    written = append_events_jsonl(jsonl, events) if append_jsonl else 0

    if persist_manifest and not sync.skipped:
        body_manifest_path(store_dir).write_text(
            json.dumps(sync.manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    diff = sync.diff
    return CatalogIngestReport(
        ok=True,
        skipped=sync.skipped,
        event_count=written if append_jsonl else len(events),
        added=len(diff.added),
        changed=len(diff.changed),
        removed=len(diff.removed),
        old_digest=diff.old_digest,
        new_digest=diff.new_digest,
        jsonl_path=str(jsonl),
        manifest_path=str(body_manifest_path(store_dir)),
        events=events,
    )
