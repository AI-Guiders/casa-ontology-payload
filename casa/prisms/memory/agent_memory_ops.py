#!/usr/bin/env python3
"""Unified agent self-memory — remember/recall any content the agent chooses."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import (
    DEFAULT_JOURNAL_DOMAIN,
    append_journal_entry,
    notebook_tag,
    search_journal_entries,
)
from casa.prisms.memory.agent_notebook import ensure_agent_notebook
from casa.prisms.memory.agent_prism import (
    create_agent_lattice,
    ensure_agent_prism,
    list_agent_lattices,
    load_agent_prism,
    place_agent_token,
    read_agent_lattice,
    save_agent_prism,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

DEFAULT_AGENT_LATTICE = "agent-self-default"
DEFAULT_JOURNAL_SCOPE = "self"


def _has_content(record: dict[str, Any]) -> bool:
    if str(record.get("text") or "").strip():
        return True
    for key in ("tokens", "concepts", "placements", "tags"):
        if record.get(key):
            return True
    data = record.get("data")
    return isinstance(data, dict) and bool(data)


def _journal_text(record: dict[str, Any]) -> str:
    text = str(record.get("text") or "").strip()
    if text:
        return text
    data = record.get("data")
    if data is not None:
        return json.dumps(data, ensure_ascii=False)[:4000]
    parts: list[str] = []
    for t in record.get("tokens") or []:
        parts.append(str(t))
    for c in record.get("concepts") or []:
        parts.append(str(c))
    return " · ".join(parts)[:4000] or "(record)"


def _ensure_default_lattice(state: dict) -> str:
    lats = ensure_agent_prism(state).setdefault("lattices", {})
    if DEFAULT_AGENT_LATTICE not in lats:
        create_agent_lattice(state, DEFAULT_AGENT_LATTICE, width=32, height=32, concept_prefix="agent.self.")
    return DEFAULT_AGENT_LATTICE


def agent_remember(
    store_dir: Path,
    state: dict,
    record: dict[str, Any],
    *,
    scope: str = DEFAULT_JOURNAL_SCOPE,
    lattice_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Persist anything the agent chose to keep — encoding is internal."""
    if not _has_content(record):
        raise ValueError("remember record needs text, tokens, concepts, placements, data, or tags")

    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    load_agent_prism(store_dir, state)

    kind = str(record.get("kind") or "observation")
    tags = [str(t) for t in (record.get("tags") or [])]
    notebook = str(record.get("notebook") or "").strip() or None
    if notebook and record.get("create_notebook"):
        ensure_agent_notebook(
            store_dir,
            notebook,
            title=str(record.get("notebook_title") or notebook),
        )
    if notebook:
        tags.append(notebook_tag(notebook))

    meta: dict[str, Any] = {"scope": scope}
    if notebook:
        meta["notebook"] = notebook
    if record.get("links"):
        meta["links"] = [str(x) for x in record["links"] if str(x).strip()]
    if record.get("data") is not None:
        meta["data"] = record["data"]
    if record.get("placements"):
        meta["placements"] = record["placements"]
    if record.get("status"):
        meta["status"] = str(record["status"])
    if record.get("test_cues"):
        meta["test_cues"] = [str(c) for c in record["test_cues"] if str(c).strip()]
    if record.get("draft"):
        meta["draft"] = True
        if "draft" not in tags:
            tags.append("draft")

    entry = append_journal_entry(
        store_dir,
        {
            "kind": kind,
            "text": _journal_text(record),
            "concepts": list(record.get("concepts") or []),
            "tokens": list(record.get("tokens") or []),
            "tags": tags,
            "meta": meta,
        },
        domain=scope,
    )

    placed: list[dict[str, Any]] = []
    target = lattice_id or DEFAULT_AGENT_LATTICE
    placements = list(record.get("placements") or [])
    tokens = list(record.get("tokens") or [])

    if placements or tokens:
        _ensure_default_lattice(state)
        if lattice_id and lattice_id != DEFAULT_AGENT_LATTICE:
            from casa.prisms.memory.agent_prism import safe_agent_lattice_id

            safe_agent_lattice_id(lattice_id)
            lats = ensure_agent_prism(state)["lattices"]
            if lattice_id not in lats:
                create_agent_lattice(state, lattice_id)

        lid = lattice_id or DEFAULT_AGENT_LATTICE
        for row in placements:
            if not isinstance(row, dict):
                continue
            tok = str(row.get("token") or "").strip()
            if not tok:
                continue
            placed.append(
                place_agent_token(
                    state,
                    lid,
                    tok,
                    x=row.get("x"),
                    y=row.get("y"),
                    copies=int(row.get("copies") or 1),
                )
            )
        for tok in tokens:
            if any(p.get("token") == tok for p in placed):
                continue
            placed.append(place_agent_token(state, lid, str(tok), copies=1))

    result: dict[str, Any] = {
        "remembered": True,
        "journal_id": entry["id"],
        "scope": scope,
        "kind": kind,
        "field_placements": len(placed),
    }
    if placed:
        result["lattice_id"] = placed[0].get("lattice_id")

    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)

    return result


def agent_recall(
    store_dir: Path,
    state: dict | None = None,
    *,
    scope: str | None = DEFAULT_JOURNAL_SCOPE,
    query: str | None = None,
    concept: str | None = None,
    tag: str | None = None,
    tags: list[str] | None = None,
    notebook: str | None = None,
    kind: str | None = None,
    draft: bool | None = None,
    limit: int = 50,
    include_field: bool = False,
) -> dict[str, Any]:
    """Unified recall from agent self-memory index (+ optional field decode)."""
    store_dir = store_dir.resolve()
    all_scopes = scope in (None, "", "*")
    tag_filter = list(tags or [])
    if tag:
        tag_filter.append(tag)

    rows = search_journal_entries(
        store_dir,
        domain=None if all_scopes else scope,
        kind=kind,
        concept=concept,
        tags=tag_filter or None,
        notebook=notebook,
        query=query,
        draft=draft,
        limit=limit,
    )
    records = [{k: v for k, v in row.items() if k != "_domain"} for row in rows]

    out: dict[str, Any] = {
        "scope": "*" if all_scopes else scope,
        "count": len(records),
        "records": records,
    }

    if include_field and state is not None:
        load_agent_prism(store_dir, state)
        field_rows: list[dict[str, Any]] = []
        for lat in list_agent_lattices(state):
            lid = str(lat["lattice_id"])
            field_rows.append(read_agent_lattice(state, lid))
        out["agent_lattices"] = field_rows

    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Agent self-memory — remember/recall anything")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_remember = sub.add_parser("remember")
    sp_remember.add_argument("--store-dir", type=Path, required=True)
    sp_remember.add_argument("--record", type=Path, default=None, help="JSON record file")
    sp_remember.add_argument("--text", default=None)
    sp_remember.add_argument("--scope", default=DEFAULT_JOURNAL_SCOPE)
    sp_remember.add_argument("--kind", default="observation")
    sp_remember.add_argument("--concepts", nargs="*", default=[])
    sp_remember.add_argument("--tokens", nargs="*", default=[])
    sp_remember.add_argument("--tags", nargs="*", default=[])
    sp_remember.add_argument("--notebook", default=None)
    sp_remember.add_argument("--links", nargs="*", default=[])

    sp_recall = sub.add_parser("recall")
    sp_recall.add_argument("--store-dir", type=Path, required=True)
    sp_recall.add_argument("--scope", default=DEFAULT_JOURNAL_SCOPE, help="Shard label or * for all")
    sp_recall.add_argument("--query", default=None)
    sp_recall.add_argument("--concept", default=None)
    sp_recall.add_argument("--tag", default=None)
    sp_recall.add_argument("--tags", nargs="*", default=[])
    sp_recall.add_argument("--notebook", default=None)
    sp_recall.add_argument("--kind", default=None)
    sp_recall.add_argument("--draft", action="store_true")
    sp_recall.add_argument("--limit", type=int, default=50)
    sp_recall.add_argument("--include-field", action="store_true")

    sp_nb = sub.add_parser("notebook")
    nb_sub = sp_nb.add_subparsers(dest="nb_cmd", required=True)
    sp_nb_create = nb_sub.add_parser("create")
    sp_nb_create.add_argument("--store-dir", type=Path, required=True)
    sp_nb_create.add_argument("--id", required=True)
    sp_nb_create.add_argument("--title", default="")
    sp_nb_create.add_argument("--intro", default=None)
    sp_nb_list = nb_sub.add_parser("list")
    sp_nb_list.add_argument("--store-dir", type=Path, required=True)

    args = p.parse_args()
    store_dir = args.store_dir.resolve()

    if args.cmd == "remember":
        if args.record:
            record = json.loads(args.record.read_text(encoding="utf-8"))
        else:
            record = {
                "kind": args.kind,
                "text": args.text or "",
                "concepts": args.concepts,
                "tokens": args.tokens,
                "tags": args.tags,
                "notebook": args.notebook,
                "links": args.links or None,
            }
        fs = field_state_path(store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        out = agent_remember(store_dir, state, record, scope=args.scope)
    elif args.cmd == "notebook":
        from casa.prisms.memory.agent_notebook import create_agent_notebook, list_agent_notebooks

        if args.nb_cmd == "create":
            out = create_agent_notebook(
                store_dir,
                args.id,
                title=args.title,
                intro=args.intro,
            )
        else:
            out = {"notebooks": list_agent_notebooks(store_dir)}
    else:
        fs = field_state_path(store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() and args.include_field else None
        scope = None if args.scope.strip() in ("", "*") else args.scope
        out = agent_recall(
            store_dir,
            state,
            scope=scope,
            query=args.query,
            concept=args.concept,
            tag=args.tag,
            tags=args.tags or None,
            notebook=args.notebook,
            kind=args.kind,
            draft=True if args.draft else None,
            limit=args.limit,
            include_field=args.include_field,
        )

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
