#!/usr/bin/env python3
"""
Extract a lightweight ontology graph from Markdown.

Goal: mirror how KB (agent-notes) behaves: nodes = md files, edges = links.

This is *not* an RDF/RDL system: it's a pragmatic graph for experiments.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
from dataclasses import dataclass, asdict
from pathlib import Path


MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BARE_URL_RE = re.compile(r"(?<!\()https?://[^\s)]+")


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    title: str | None = None


@dataclass(frozen=True)
class Edge:
    src: str
    relation: str
    dst: str
    label: str | None = None


def _guess_kind(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("work/projects/"):
        return "project_doc"
    if p.startswith("worlds/"):
        return "world_doc"
    if p.startswith("domains/"):
        return "domain_doc"
    if p.startswith("META/"):
        return "meta_doc"
    if p.startswith("adr/"):
        return "kb_adr"
    if p.endswith(".md"):
        return "md"
    return "external"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or None
    return None


def extract_graph(md_path: Path, *, root_id: str | None = None) -> dict:
    text = _read_text(md_path)
    title = _first_h1(text) or md_path.stem
    root_id = root_id or md_path.as_posix()
    root = Node(id=root_id, kind=_guess_kind(root_id), title=title)
    root_dir = str(Path(root_id).parent).replace("\\", "/")

    nodes: dict[str, Node] = {root.id: root}
    edges: list[Edge] = []

    for label, target in MD_LINK_RE.findall(text):
        target = target.strip()
        if not target or target.startswith("#"):
            continue

        if target.startswith("http://") or target.startswith("https://"):
            dst = target
            if dst not in nodes:
                nodes[dst] = Node(id=dst, kind="url", title=None)
            edges.append(Edge(src=root.id, relation="references", dst=dst, label=label.strip() or None))
            continue

        dst = target.replace("\\", "/")
        if dst.endswith(".md") and not dst.startswith(("work/", "worlds/", "domains/", "META/", "adr/")):
            dst = f"{root_dir}/{dst}".replace("\\", "/")
        dst = posixpath.normpath(dst)
        if dst not in nodes:
            nodes[dst] = Node(id=dst, kind=_guess_kind(dst), title=None)
        edges.append(Edge(src=root.id, relation="references", dst=dst, label=label.strip() or None))

    for url in BARE_URL_RE.findall(text):
        if url not in nodes:
            nodes[url] = Node(id=url, kind="url", title=None)
        edges.append(Edge(src=root.id, relation="references", dst=url, label=None))

    return {"root": asdict(root), "nodes": [asdict(n) for n in nodes.values()], "edges": [asdict(e) for e in edges]}


def main() -> None:
    p = argparse.ArgumentParser(description="Extract lightweight ontology graph from a Markdown file")
    p.add_argument("md_path", type=Path)
    p.add_argument("--root-id", default=None, help="Override node id (e.g. knowledge-relative path)")
    p.add_argument("--out", type=Path, default=None, help="Output JSON path (default: stdout)")
    args = p.parse_args()

    g = extract_graph(args.md_path, root_id=args.root_id)
    data = json.dumps(g, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    else:
        print(data)


if __name__ == "__main__":
    main()

