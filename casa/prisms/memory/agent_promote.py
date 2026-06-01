#!/usr/bin/env python3
"""Explicit Self → profile promote — journal draft/law into hippo + sleep consolidate."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import find_journal_entry, patch_journal_entry
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _meta(entry: dict[str, Any]) -> dict[str, Any]:
    m = entry.get("meta")
    return dict(m) if isinstance(m, dict) else {}


def _graph_links(meta: dict[str, Any]) -> list[dict[str, Any]] | None:
    raw = meta.get("graph_links") or meta.get("promote_edges")
    if not isinstance(raw, list):
        return None
    out: list[dict[str, Any]] = []
    for row in raw[:12]:
        if not isinstance(row, dict):
            continue
        src = str(row.get("src") or "").strip()
        rel = str(row.get("relation") or row.get("rel") or "").strip()
        dst = str(row.get("dst") or "").strip()
        if src and rel and dst:
            out.append({"src": src, "relation": rel, "dst": dst})
    return out or None


def promote_journal_entry(
    store_dir: Path,
    state: dict,
    entry_id: str,
    bundle: dict,
    *,
    lattice_id: str = SCHEMA_MATH,
    require_status: str | None = "confirmed",
    allow_unconfirmed: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    """Move one Self journal row into profile path: hippo episode → sleep → field strengthen."""
    found = find_journal_entry(store_dir, entry_id)
    if found is None:
        raise ValueError(f"journal entry not found: {entry_id}")
    row, shard = found
    meta = _meta(row)

    if meta.get("promoted"):
        return {
            "promoted": False,
            "reason": "already_promoted",
            "entry_id": entry_id,
            "journal_shard": shard,
        }

    status = str(meta.get("status") or "")
    if require_status and status != require_status and not allow_unconfirmed:
        raise ValueError(
            f"entry status {status!r} != required {require_status!r} "
            "(use allow_unconfirmed or workbook_check first)"
        )

    concepts = [str(c) for c in (row.get("concepts") or []) if c]
    concept_id = concepts[0] if concepts else None
    text = str(row.get("text") or "").strip()
    test_cues = [str(c) for c in (meta.get("test_cues") or []) if str(c).strip()]
    cue = test_cues[0] if test_cues else text[:120]
    correct = concept_id or text[:120]

    state = ensure_prisms(state)
    ep = append_episode(
        state,
        cue=cue,
        surface_attempt="?",
        correct=correct,
        lattice_id=lattice_id,
        concept_id=concept_id,
        bundle=bundle,
        scene="agent_promote",
        structure_tag="self_promote",
        links=_graph_links(meta),
    )
    sleep_rep = run_sleep(state, bundle)

    meta.update(
        {
            "promoted": True,
            "promote_episode_id": ep.get("id"),
            "promote_sleep": {
                "merged": int(sleep_rep.get("merged") or 0),
                "pending": int(sleep_rep.get("pending") or 0),
            },
        }
    )
    patched = patch_journal_entry(store_dir, entry_id, {"meta": meta}, domain=shard)

    result: dict[str, Any] = {
        "promoted": True,
        "entry_id": entry_id,
        "journal_shard": shard,
        "episode_id": ep.get("id"),
        "concept_id": concept_id,
        "sleep": sleep_rep,
        "entry": patched,
    }

    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state)

    return result


def main() -> None:
    p = argparse.ArgumentParser(description="Promote Self journal entry → profile field (hippo + sleep)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--id", required=True, help="Journal entry id (j-…)")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--lattice-id", default=SCHEMA_MATH)
    p.add_argument(
        "--require-status",
        default="confirmed",
        help="Draft status required before promote (empty = any)",
    )
    p.add_argument("--allow-unconfirmed", action="store_true")
    args = p.parse_args()

    store_dir = args.store_dir.resolve()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({})

    req = args.require_status.strip() or None
    print(
        json.dumps(
            promote_journal_entry(
                store_dir,
                state,
                args.id,
                bundle,
                lattice_id=args.lattice_id,
                require_status=req,
                allow_unconfirmed=args.allow_unconfirmed,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
