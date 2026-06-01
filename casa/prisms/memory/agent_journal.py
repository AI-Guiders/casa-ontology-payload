#!/usr/bin/env python3
"""Agent-owned journal on disk — independent from ltm/ cartridges."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.store_layout import journal_domain_dir, journal_entries_path, journal_index_path, journal_root

JOURNAL_SCHEMA_VERSION = 1
DEFAULT_JOURNAL_DOMAIN = "self"
_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_ENTRY_KINDS = frozenset(
    {
        "law",
        "episode",
        "note",
        "hypothesis",
        "observation",
        "question",
        "check",
        "experiment",
        "draft",
    }
)
NOTEBOOK_TAG_PREFIX = "notebook:"


def safe_journal_domain(domain: str) -> str:
    d = str(domain or "").strip().lower()
    if not _DOMAIN_RE.fullmatch(d):
        raise ValueError(f"invalid journal domain: {domain!r}")
    return d


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_entry_id() -> str:
    return f"j-{uuid.uuid4().hex[:12]}"


def _load_index(store_dir: Path) -> dict[str, Any]:
    path = journal_index_path(store_dir)
    if not path.is_file():
        return {"schema_version": JOURNAL_SCHEMA_VERSION, "domains": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("schema_version", JOURNAL_SCHEMA_VERSION)
    data.setdefault("domains", {})
    return data


def _save_index(store_dir: Path, index: dict[str, Any]) -> None:
    root = journal_root(store_dir)
    root.mkdir(parents=True, exist_ok=True)
    journal_index_path(store_dir).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_entries(store_dir: Path, domain: str) -> list[dict[str, Any]]:
    path = journal_entries_path(store_dir, domain)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _write_entries(store_dir: Path, domain: str, rows: list[dict[str, Any]]) -> None:
    domain_dir = journal_domain_dir(store_dir, domain)
    domain_dir.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    journal_entries_path(store_dir, domain).write_text(text, encoding="utf-8")


def notebook_tag(notebook: str) -> str:
    nb = str(notebook or "").strip()
    if not nb:
        raise ValueError("notebook name is required")
    return f"{NOTEBOOK_TAG_PREFIX}{nb}"


def list_journal_domains(store_dir: Path) -> list[str]:
    """FS shard names under journal/ (agent-chosen scope labels, not ontology)."""
    store_dir = store_dir.resolve()
    names: set[str] = set()
    index = _load_index(store_dir)
    names.update(str(k) for k in (index.get("domains") or {}))
    root = journal_root(store_dir)
    if root.is_dir():
        for child in root.iterdir():
            if child.is_dir() and (child / "entries.jsonl").is_file():
                names.add(child.name)
    return sorted(names)


def _entry_matches_filters(
    row: dict[str, Any],
    *,
    kind: str | None,
    kinds: frozenset[str] | None,
    concept: str | None,
    tags: list[str] | None,
    notebook: str | None,
    query: str | None,
    draft: bool | None,
) -> bool:
    if kind and row.get("kind") != kind:
        return False
    if kinds and row.get("kind") not in kinds:
        return False
    if concept:
        needle = str(concept)
        if needle not in (row.get("concepts") or []):
            return False
    row_tags = [str(t) for t in (row.get("tags") or [])]
    if tags:
        needed = {str(t) for t in tags}
        if not needed.issubset(set(row_tags)):
            return False
    if notebook:
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        nb_tag = notebook_tag(notebook)
        if (
            str(meta.get("notebook") or "") != notebook
            and nb_tag not in row_tags
            and notebook not in row_tags
        ):
            return False
    if draft is True:
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if "draft" not in row_tags and not meta.get("draft"):
            return False
    if draft is False:
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if "draft" in row_tags or meta.get("draft"):
            return False
    if query:
        needle = query.casefold()
        hay = str(row.get("text") or "").casefold()
        meta_hay = json.dumps(row.get("meta") or {}, ensure_ascii=False).casefold()
        if needle not in hay and needle not in meta_hay:
            return False
    return True


def search_journal_entries(
    store_dir: Path,
    *,
    domain: str | None = None,
    kind: str | None = None,
    kinds: frozenset[str] | None = None,
    concept: str | None = None,
    tags: list[str] | None = None,
    notebook: str | None = None,
    query: str | None = None,
    draft: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Cross-shard search; each row includes `_domain` (FS shard, agent scope label)."""
    store_dir = store_dir.resolve()
    shards = [safe_journal_domain(domain)] if domain else list_journal_domains(store_dir)
    out: list[dict[str, Any]] = []
    for shard in shards:
        for row in _load_entries(store_dir, shard):
            if not _entry_matches_filters(
                row,
                kind=kind,
                kinds=kinds,
                concept=concept,
                tags=tags,
                notebook=notebook,
                query=query,
                draft=draft,
            ):
                continue
            tagged = dict(row)
            tagged["_domain"] = shard
            out.append(tagged)
    if limit > 0:
        out = out[-limit:]
    return out


def find_journal_entry(
    store_dir: Path,
    entry_id: str,
    *,
    domain: str | None = None,
) -> tuple[dict[str, Any], str] | None:
    store_dir = store_dir.resolve()
    shards = [safe_journal_domain(domain)] if domain else list_journal_domains(store_dir)
    for shard in shards:
        for row in _load_entries(store_dir, shard):
            if row.get("id") == entry_id:
                return row, shard
    return None


def _touch_domain_index(store_dir: Path, domain: str, *, entry_count: int) -> None:
    index = _load_index(store_dir)
    domains = index.setdefault("domains", {})
    domains[domain] = {
        "entry_count": entry_count,
        "updated_at": _utc_now(),
        "entries_path": journal_entries_path(store_dir, domain).name,
    }
    _save_index(store_dir, index)


def journal_stats(store_dir: Path) -> dict[str, Any]:
    """Summary for memory_manifest / tooling."""
    store_dir = store_dir.resolve()
    index = _load_index(store_dir)
    domains = index.get("domains") or {}
    total = 0
    domain_rows: list[dict[str, Any]] = []
    for name, meta in sorted(domains.items()):
        count = int(meta.get("entry_count") or 0)
        total += count
        domain_rows.append(
            {
                "domain": name,
                "entry_count": count,
                "updated_at": meta.get("updated_at"),
            }
        )
    entries_path = journal_root(store_dir)
    bytes_total = 0
    if entries_path.is_dir():
        for p in entries_path.rglob("*"):
            if p.is_file():
                try:
                    bytes_total += p.stat().st_size
                except OSError:
                    pass
    return {
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "domain_count": len(domain_rows),
        "entry_count": total,
        "bytes": bytes_total,
        "domains": domain_rows,
    }


def append_journal_entry(
    store_dir: Path,
    entry: dict[str, Any],
    *,
    domain: str = DEFAULT_JOURNAL_DOMAIN,
) -> dict[str, Any]:
    domain = safe_journal_domain(domain)
    kind = str(entry.get("kind") or "note")
    if kind not in _ENTRY_KINDS:
        raise ValueError(f"invalid entry kind: {kind!r}; expected one of {sorted(_ENTRY_KINDS)}")

    row: dict[str, Any] = {
        "id": str(entry.get("id") or _new_entry_id()),
        "ts": str(entry.get("ts") or _utc_now()),
        "kind": kind,
        "text": str(entry.get("text") or "").strip(),
        "concepts": [str(c) for c in (entry.get("concepts") or []) if c],
        "tokens": [str(t) for t in (entry.get("tokens") or []) if t],
        "tags": [str(t) for t in (entry.get("tags") or []) if t],
    }
    if not row["text"]:
        raise ValueError("journal entry text is required")

    meta = entry.get("meta")
    if isinstance(meta, dict) and meta:
        row["meta"] = meta

    rows = _load_entries(store_dir, domain)
    if any(r.get("id") == row["id"] for r in rows):
        raise ValueError(f"duplicate entry id: {row['id']}")

    rows.append(row)
    _write_entries(store_dir, domain, rows)
    _touch_domain_index(store_dir, domain, entry_count=len(rows))
    return row


def read_journal_entries(
    store_dir: Path,
    *,
    domain: str = DEFAULT_JOURNAL_DOMAIN,
    kind: str | None = None,
    concept: str | None = None,
    tags: list[str] | None = None,
    notebook: str | None = None,
    query: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows = search_journal_entries(
        store_dir,
        domain=domain,
        kind=kind,
        concept=concept,
        tags=tags,
        notebook=notebook,
        query=query,
        limit=limit,
    )
    return [{k: v for k, v in row.items() if k != "_domain"} for row in rows]


def get_journal_entry(
    store_dir: Path,
    entry_id: str,
    *,
    domain: str | None = None,
) -> dict[str, Any] | None:
    found = find_journal_entry(store_dir, entry_id, domain=domain)
    return found[0] if found else None


def delete_journal_entry(store_dir: Path, entry_id: str, *, domain: str | None = None) -> bool:
    found = find_journal_entry(store_dir, entry_id, domain=domain)
    if not found:
        return False
    _, shard = found
    rows = _load_entries(store_dir, shard)
    kept = [r for r in rows if r.get("id") != entry_id]
    _write_entries(store_dir, shard, kept)
    _touch_domain_index(store_dir, shard, entry_count=len(kept))
    return True


def patch_journal_entry(
    store_dir: Path,
    entry_id: str,
    patch: dict[str, Any],
    *,
    domain: str | None = None,
) -> dict[str, Any] | None:
    found = find_journal_entry(store_dir, entry_id, domain=domain)
    if not found:
        return None
    _, shard = found
    domain = shard
    rows = _load_entries(store_dir, domain)
    out: dict[str, Any] | None = None
    for i, row in enumerate(rows):
        if row.get("id") != entry_id:
            continue
        updated = dict(row)
        for key in ("text", "kind", "concepts", "tokens", "tags", "meta"):
            if key in patch:
                updated[key] = patch[key]
        if updated.get("kind") not in _ENTRY_KINDS:
            raise ValueError(f"invalid entry kind: {updated.get('kind')!r}")
        if not str(updated.get("text") or "").strip():
            raise ValueError("journal entry text is required")
        updated["updated_at"] = _utc_now()
        rows[i] = updated
        out = updated
        break
    if out is None:
        return None
    _write_entries(store_dir, domain, rows)
    _touch_domain_index(store_dir, domain, entry_count=len(rows))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Agent-owned journal (not ltm/ cartridge)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser, *, domain_default: str = DEFAULT_JOURNAL_DOMAIN) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)
        sp.add_argument("--domain", default=domain_default)

    sp_append = sub.add_parser("append", help="Append a journal entry")
    add_store(sp_append)
    sp_append.add_argument("--kind", default="note", choices=sorted(_ENTRY_KINDS))
    sp_append.add_argument("--text", required=True)
    sp_append.add_argument("--concepts", nargs="*", default=[])
    sp_append.add_argument("--tokens", nargs="*", default=[])
    sp_append.add_argument("--tags", nargs="*", default=[])
    sp_append.add_argument("--notebook", default=None, help="Optional notebook/collection label")

    sp_read = sub.add_parser("read", help="List recent entries")
    add_store(sp_read, domain_default="")
    sp_read.add_argument("--kind", default=None)
    sp_read.add_argument("--concept", default=None)
    sp_read.add_argument("--tags", nargs="*", default=[])
    sp_read.add_argument("--notebook", default=None)
    sp_read.add_argument("--query", default=None)
    sp_read.add_argument("--draft", action="store_true", help="Only draft-tagged entries")
    sp_read.add_argument("--limit", type=int, default=50)

    sp_get = sub.add_parser("get", help="Fetch one entry by id")
    add_store(sp_get, domain_default="")
    sp_get.add_argument("--id", required=True)

    sp_delete = sub.add_parser("delete", help="Delete entry by id")
    add_store(sp_delete, domain_default="")
    sp_delete.add_argument("--id", required=True)

    sp_patch = sub.add_parser("patch", help="Update entry fields")
    add_store(sp_patch, domain_default="")
    sp_patch.add_argument("--id", required=True)
    sp_patch.add_argument("--text", default=None)
    sp_patch.add_argument("--kind", default=None, choices=sorted(_ENTRY_KINDS))

    sp_stats = sub.add_parser("stats", help="Journal summary for store")
    sp_stats.add_argument("--store-dir", type=Path, required=True)

    args = p.parse_args()
    store_dir = args.store_dir.resolve()

    if args.cmd == "append":
        meta: dict[str, Any] = {}
        tags = list(args.tags)
        if args.notebook:
            meta["notebook"] = args.notebook
            tags.append(notebook_tag(args.notebook))
        row = append_journal_entry(
            store_dir,
            {
                "kind": args.kind,
                "text": args.text,
                "concepts": args.concepts,
                "tokens": args.tokens,
                "tags": tags,
                **({"meta": meta} if meta else {}),
            },
            domain=args.domain or DEFAULT_JOURNAL_DOMAIN,
        )
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return

    if args.cmd == "read":
        domain = args.domain.strip() or None
        rows = search_journal_entries(
            store_dir,
            domain=domain,
            kind=args.kind,
            concept=args.concept,
            tags=args.tags or None,
            notebook=args.notebook,
            query=args.query,
            draft=True if args.draft else None,
            limit=args.limit,
        )
        print(
            json.dumps(
                {"domain": domain or "*", "count": len(rows), "entries": rows},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "get":
        dom = args.domain.strip() or None
        row = get_journal_entry(store_dir, args.id, domain=dom)
        if row is None:
            raise SystemExit(f"entry not found: {args.id}")
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return

    if args.cmd == "delete":
        dom = args.domain.strip() or None
        ok = delete_journal_entry(store_dir, args.id, domain=dom)
        print(json.dumps({"deleted": ok, "id": args.id}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if ok else 1)

    if args.cmd == "patch":
        patch: dict[str, Any] = {}
        if args.text is not None:
            patch["text"] = args.text
        if args.kind is not None:
            patch["kind"] = args.kind
        dom = args.domain.strip() or None
        row = patch_journal_entry(store_dir, args.id, patch, domain=dom)
        if row is None:
            raise SystemExit(f"entry not found: {args.id}")
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return

    if args.cmd == "stats":
        print(json.dumps(journal_stats(store_dir), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
