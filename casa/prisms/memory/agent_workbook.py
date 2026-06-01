#!/usr/bin/env python3
"""Draft workbook — hypotheses, experiments, checks on Self journal (not a fixed domain)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import (
    DEFAULT_JOURNAL_DOMAIN,
    find_journal_entry,
    notebook_tag,
    patch_journal_entry,
    search_journal_entries,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

_DRAFT_KINDS = frozenset({"hypothesis", "question", "note", "check", "law", "experiment", "draft"})
_STATUSES = frozenset({"open", "testing", "confirmed", "rejected", "unclear"})


def _meta(entry: dict[str, Any]) -> dict[str, Any]:
    m = entry.get("meta")
    return dict(m) if isinstance(m, dict) else {}


def _draft_tags(*, notebook: str | None, tags: list[str] | None) -> list[str]:
    out = ["draft", *(tags or [])]
    if notebook:
        out.append(notebook_tag(notebook))
    return out


def workbook_write(
    store_dir: Path,
    *,
    kind: str,
    text: str,
    concepts: list[str] | None = None,
    test_cues: list[str] | None = None,
    expect: str | None = None,
    tags: list[str] | None = None,
    status: str = "open",
    scope: str = DEFAULT_JOURNAL_DOMAIN,
    notebook: str | None = None,
    links: list[str] | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a draft row to Self journal — optional notebook/collection, any scope shard."""
    from casa.prisms.memory.agent_journal import append_journal_entry

    kind = str(kind or "note")
    if kind not in _DRAFT_KINDS:
        raise ValueError(f"workbook kind must be one of {sorted(_DRAFT_KINDS)}")
    st = str(status or "open")
    if st not in _STATUSES:
        raise ValueError(f"status must be one of {sorted(_STATUSES)}")

    meta: dict[str, Any] = {
        "draft": True,
        "status": st,
        "test_cues": [str(c).strip() for c in (test_cues or []) if str(c).strip()],
        "checks": [],
    }
    if notebook:
        meta["notebook"] = notebook
    if links:
        meta["links"] = [str(x) for x in links if str(x).strip()]
    if expect:
        meta["expect"] = str(expect)
    if extra_meta:
        meta.update(extra_meta)

    row = append_journal_entry(
        store_dir,
        {
            "kind": kind,
            "text": text.strip(),
            "concepts": list(concepts or []),
            "tags": _draft_tags(notebook=notebook, tags=tags),
            "meta": meta,
        },
        domain=scope,
    )
    return row


def workbook_list(
    store_dir: Path,
    *,
    kind: str | None = None,
    status: str | None = None,
    concept: str | None = None,
    notebook: str | None = None,
    scope: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    kinds = _DRAFT_KINDS if kind is None else frozenset({kind})
    rows = search_journal_entries(
        store_dir,
        domain=scope,
        kinds=kinds,
        concept=concept,
        notebook=notebook,
        draft=True,
        limit=0,
    )
    if status:
        rows = [r for r in rows if _meta(r).get("status") == status]
    if limit > 0:
        rows = rows[-limit:]
    return [{k: v for k, v in row.items() if k != "_domain"} for row in rows]


def workbook_open_questions(
    store_dir: Path,
    *,
    notebook: str | None = None,
    scope: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Open hypotheses and unanswered questions for the agent to revisit."""
    rows = workbook_list(store_dir, notebook=notebook, scope=scope, limit=0)
    out = [
        r
        for r in rows
        if _meta(r).get("status") in ("open", "testing", "unclear")
        and r.get("kind") in ("hypothesis", "question", "experiment")
    ]
    return out[-limit:] if limit > 0 else out


def workbook_check(
    store_dir: Path,
    state: dict,
    entry_id: str,
    bundle: dict | None = None,
    *,
    modality: str = "schema",
    test_cues: list[str] | None = None,
    expect: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run predict on workbook test cues; update status from critic verdict."""
    found = find_journal_entry(store_dir, entry_id)
    if found is None:
        raise ValueError(f"workbook entry not found: {entry_id}")
    row, shard = found

    meta = _meta(row)
    cues = test_cues or list(meta.get("test_cues") or [])
    if not cues:
        raise ValueError("no test_cues on entry or call")

    target = expect or meta.get("expect") or (row.get("concepts") or [None])[0]
    state = ensure_prisms(state)
    runs: list[dict[str, Any]] = []
    passes = 0
    for cue in cues:
        tick = predict_tick(state, cue, modality=modality, expect=target, bundle=bundle)
        ok = tick.get("verdict") == "pass" or (
            target
            and tick.get("predict", {}).get("hypothesis") == target
            and not tick.get("predict", {}).get("unbound_operators")
        )
        if ok:
            passes += 1
        runs.append(
            {
                "cue": cue,
                "expect": target,
                "verdict": tick.get("verdict"),
                "hypothesis": tick.get("predict", {}).get("hypothesis"),
                "unbound": tick.get("predict", {}).get("unbound_operators"),
            }
        )

    ratio = passes / len(cues)
    if ratio >= 1.0:
        new_status = "confirmed"
    elif ratio <= 0.0:
        new_status = "rejected"
    elif ratio >= 0.5:
        new_status = "unclear"
    else:
        new_status = "testing"

    checks = list(meta.get("checks") or [])
    checks.append({"runs": runs, "passes": passes, "total": len(cues), "status": new_status})
    meta["status"] = new_status
    meta["checks"] = checks[-12:]
    meta["last_check"] = runs

    patched = patch_journal_entry(
        store_dir,
        entry_id,
        {"meta": meta},
        domain=shard,
    )
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state)

    return {
        "entry_id": entry_id,
        "status": new_status,
        "passes": passes,
        "total": len(cues),
        "runs": runs,
        "entry": patched,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Agent workbook (draft hypotheses / experiments / checks)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)

    sp_w = sub.add_parser("write")
    add_store(sp_w)
    sp_w.add_argument("--kind", default="hypothesis", choices=sorted(_DRAFT_KINDS))
    sp_w.add_argument("--text", required=True)
    sp_w.add_argument("--concepts", nargs="*", default=[])
    sp_w.add_argument("--test-cues", nargs="*", default=[])
    sp_w.add_argument("--expect", default=None)
    sp_w.add_argument("--status", default="open", choices=sorted(_STATUSES))
    sp_w.add_argument("--scope", default=DEFAULT_JOURNAL_DOMAIN)
    sp_w.add_argument("--notebook", default=None)
    sp_w.add_argument("--links", nargs="*", default=[])

    sp_l = sub.add_parser("list")
    add_store(sp_l)
    sp_l.add_argument("--kind", default=None)
    sp_l.add_argument("--status", default=None)
    sp_l.add_argument("--notebook", default=None)
    sp_l.add_argument("--scope", default=None)
    sp_l.add_argument("--limit", type=int, default=50)

    sp_o = sub.add_parser("open")
    add_store(sp_o)
    sp_o.add_argument("--notebook", default=None)
    sp_o.add_argument("--scope", default=None)
    sp_o.add_argument("--limit", type=int, default=50)

    sp_c = sub.add_parser("check")
    add_store(sp_c)
    sp_c.add_argument("--id", required=True)
    sp_c.add_argument("--bundle", type=Path, default=None)
    sp_c.add_argument("--modality", default="schema")
    sp_c.add_argument("--test-cues", nargs="*", default=[])
    sp_c.add_argument("--expect", default=None)

    args = p.parse_args()
    store_dir = args.store_dir.resolve()

    if args.cmd == "write":
        print(
            json.dumps(
                workbook_write(
                    store_dir,
                    kind=args.kind,
                    text=args.text,
                    concepts=args.concepts,
                    test_cues=args.test_cues,
                    expect=args.expect,
                    status=args.status,
                    scope=args.scope,
                    notebook=args.notebook,
                    links=args.links or None,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "list":
        rows = workbook_list(
            store_dir,
            kind=args.kind,
            status=args.status,
            notebook=args.notebook,
            scope=args.scope,
            limit=args.limit,
        )
        print(json.dumps({"count": len(rows), "entries": rows}, ensure_ascii=False, indent=2))
        return

    if args.cmd == "open":
        rows = workbook_open_questions(store_dir, notebook=args.notebook, scope=args.scope, limit=args.limit)
        print(json.dumps({"count": len(rows), "entries": rows}, ensure_ascii=False, indent=2))
        return

    if args.cmd == "check":
        bundle = None
        if args.bundle:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        fs = field_state_path(store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({})
        print(
            json.dumps(
                workbook_check(
                    store_dir,
                    state,
                    args.id,
                    bundle,
                    modality=args.modality,
                    test_cues=args.test_cues or None,
                    expect=args.expect,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return


if __name__ == "__main__":
    main()
