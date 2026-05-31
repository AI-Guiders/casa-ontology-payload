#!/usr/bin/env python3
"""
Build a single ontology bundle from:
- graph.json (nodes + edges)
- one or more payload.json files (claims with optional concept_id)

The bundle is the "thing we will encode in field" (later).
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Build ontology bundle JSON")
    p.add_argument("--graph", type=Path, required=True)
    p.add_argument("--payload", type=Path, action="append", default=[], help="Repeatable payload JSON(s)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    graph = _read_json(args.graph)
    payloads = [_read_json(x) for x in args.payload]

    claims = []
    concept_labels: dict[str, list[str]] = defaultdict(list)
    for pl in payloads:
        for c in pl.get("claims", []):
            claims.append(c)
            cid = c.get("concept_id")
            txt = c.get("text")
            if cid and txt:
                concept_labels[cid].append(txt)

    # pick a short label per concept_id (first seen)
    concept_index = [{"concept_id": cid, "label": labels[0]} for cid, labels in sorted(concept_labels.items())]

    bundle = {
        "schema_version": 1,
        "graph": graph,
        "claims": claims,
        "concept_index": concept_index,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

