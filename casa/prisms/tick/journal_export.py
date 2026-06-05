#!/usr/bin/env python3
"""Export agent_journal tables to JSONL.gz (ADR-0038 lab archive)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import gzip
import json
from pathlib import Path

from casa.domain.agent_journal import journal_path, open_journal


def _export_table(store_dir: Path, table: str, out: Path) -> int:
    count = 0
    with open_journal(store_dir) as conn:
        rows = conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for row in rows:
            payload = row["payload"]
            try:
                doc = json.loads(payload)
            except json.JSONDecodeError:
                doc = {"raw": payload}
            doc["_table"] = table
            fh.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def main() -> int:
    p = argparse.ArgumentParser(description="Export agent journal to JSONL.gz")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument(
        "--table",
        choices=("skill_trace", "tick_log", "experience", "retrospective", "all"),
        default="all",
    )
    p.add_argument("--out-dir", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    out_dir = args.out_dir or (store / "lab" / "journal-export")
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = (
        ["skill_trace", "tick_log", "experience", "retrospective"]
        if args.table == "all"
        else [args.table]
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "journal": str(journal_path(store)),
        "exports": {},
    }
    for table in tables:
        dest = out_dir / f"{table}.jsonl.gz"
        n = _export_table(store, table, dest)
        report["exports"][table] = {"path": str(dest), "rows": n}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
