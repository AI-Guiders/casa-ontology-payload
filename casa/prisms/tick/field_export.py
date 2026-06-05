#!/usr/bin/env python3
"""Export agent_field.db for inspection (ADR-0039)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import gzip
import json
from pathlib import Path

from casa.domain.agent_field import field_db_path, field_db_stats, import_field_from_json, open_field_db


def main() -> int:
    p = argparse.ArgumentParser(description="Export or inspect agent_field.db")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument("--stats", action="store_true", help="Show route/chunk stats only")
    p.add_argument("--import-json", type=Path, default=None, help="Migrate field_state.json into db")
    p.add_argument("--export-body", type=Path, default=None, help="Decompress field_body chunk to JSON file")
    p.add_argument("--export-routes", type=Path, default=None, help="Write routes as JSON array")
    args = p.parse_args()

    store = args.store_dir.resolve()
    if args.import_json:
        rep = import_field_from_json(store, args.import_json)
        print(json.dumps({"imported": rep}, indent=2))
        return 0

    if args.stats or (not args.export_body and not args.export_routes):
        print(json.dumps(field_db_stats(store), indent=2))
        if args.stats:
            return 0

    if not field_db_path(store).is_file():
        print(json.dumps({"error": "agent_field.db not found"}, indent=2))
        return 1

    with open_field_db(store) as conn:
        if args.export_body:
            row = conn.execute("SELECT blob FROM chunks WHERE name='field_body'").fetchone()
            if row is None:
                return 1
            body = gzip.decompress(row["blob"])
            args.export_body.parent.mkdir(parents=True, exist_ok=True)
            args.export_body.write_bytes(body)
            print(json.dumps({"exported_body": str(args.export_body), "bytes": len(body)}, indent=2))
        if args.export_routes:
            rows = conn.execute("SELECT route_kind, priority, match_json, target_prism, target_skill, target_goal, target_plan, steps_json FROM routes ORDER BY id").fetchall()
            routes = []
            for r in rows:
                routes.append(
                    {
                        "route_kind": r["route_kind"],
                        "priority": r["priority"],
                        "match": json.loads(r["match_json"]),
                        "target_prism": r["target_prism"],
                        "target_skill": r["target_skill"],
                        "target_goal": r["target_goal"],
                        "target_plan": r["target_plan"],
                        "steps": json.loads(r["steps_json"] or "[]"),
                    }
                )
            args.export_routes.parent.mkdir(parents=True, exist_ok=True)
            args.export_routes.write_text(json.dumps(routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"exported_routes": str(args.export_routes), "count": len(routes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
