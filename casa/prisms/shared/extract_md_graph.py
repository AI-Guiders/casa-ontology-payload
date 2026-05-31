#!/usr/bin/env python3
"""Extract a minimal link graph from Markdown (knowledge-relative paths)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from pathlib import Path

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
ROOT_ID_RE = re.compile(r"^#{1,6}\s+")


def _norm_path(raw: str, *, md_file: Path, root_id: str) -> str | None:
    target = raw.strip().split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("knowledge/"):
        return target.replace("\\", "/")
    if target.endswith(".md"):
        if "/" in target or "\\" in target:
            return target.replace("\\", "/")
        return target.replace("\\", "/")
    return None


def extract_graph(md_text: str, *, root_id: str, md_path: Path | None = None) -> dict:
    root_id = root_id.replace("\\", "/")
    title = Path(root_id).stem
    nodes: dict[str, dict] = {
        root_id: {"id": root_id, "kind": "project_doc", "title": title},
    }
    edges: list[dict] = []

    for m in LINK_RE.finditer(md_text):
        label = m.group(1).strip() or None
        dst = _norm_path(m.group(2), md_file=md_path or Path(root_id), root_id=root_id)
        if not dst:
            continue
        if dst not in nodes:
            kind = "project_doc" if dst.startswith("work/") else "md"
            nodes[dst] = {"id": dst, "kind": kind, "title": Path(dst).stem}
        edges.append(
            {
                "src": root_id,
                "relation": "references",
                "dst": dst,
                "label": label,
            }
        )

    return {
        "root": {"id": root_id, "kind": "project_doc", "title": title},
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Extract graph from Markdown links")
    p.add_argument("md_path", type=Path)
    p.add_argument("--root-id", required=True, help="knowledge-relative doc id")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    text = args.md_path.read_text(encoding="utf-8", errors="replace")
    graph = extract_graph(text, root_id=args.root_id, md_path=args.md_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
