#!/usr/bin/env python3
"""Meaning frame authoring — journal hypothesis → bundle promote (ADR-0053)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def journal_hypothesis_frames(
    store_dir: Path,
    *,
    min_occurrences: int = 2,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Draft meaning_frame rows from journal prop_ids (agent-side hypotheses)."""
    from casa.prisms.memory.agent_journal import search_journal_entries

    counts: dict[str, int] = {}
    samples: dict[str, dict[str, Any]] = {}
    for row in search_journal_entries(store_dir, domain="self", limit=80):
        data = (row.get("meta") or {}).get("data") if isinstance(row.get("meta"), dict) else {}
        if not isinstance(data, dict):
            data = {}
        prop_ids = list(row.get("concepts") or []) + list(data.get("prop_ids") or [])
        for pid in prop_ids:
            pid = str(pid).strip()
            if not pid.startswith("ru.prop."):
                continue
            counts[pid] = counts.get(pid, 0) + 1
            if pid not in samples:
                samples[pid] = {
                    "concept_id": pid,
                    "text": str(row.get("text") or "")[:200],
                    "section": "meaning_frame",
                    "slots": {"score": "28", "source": "journal_hypothesis"},
                    "test_cues": list(data.get("test_cues") or [])[:3],
                }
    out = [samples[cid] for cid, n in sorted(counts.items(), key=lambda x: -x[1]) if n >= min_occurrences]
    return out[:limit]


def promote_frame_from_journal(
    store_dir: Path,
    *,
    bundle_path: Path | None = None,
    min_occurrences: int = 2,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Merge journal-stable prop hypotheses into semantics bundle (teacher compile)."""
    store_dir = store_dir.resolve()
    path = bundle_path or (store_dir / "bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json")
    if not path.is_file():
        raise FileNotFoundError(path)

    bundle = json.loads(path.read_text(encoding="utf-8"))
    claims = list(bundle.get("claims") or [])
    by_id = {str(c.get("concept_id") or ""): c for c in claims if c.get("concept_id")}
    drafts = journal_hypothesis_frames(store_dir, min_occurrences=min_occurrences)
    added: list[str] = []
    for draft in drafts:
        cid = str(draft.get("concept_id") or "")
        if not cid or cid in by_id:
            continue
        claims.append(draft)
        by_id[cid] = draft
        added.append(cid)

    if added and not dry_run:
        bundle["claims"] = claims
        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"bundle": str(path), "added": added, "dry_run": dry_run, "total_claims": len(claims)}
