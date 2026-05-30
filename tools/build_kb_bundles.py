#!/usr/bin/env python3
"""
Build ontology bundles from agent-notes KB Markdown (manifest-driven).

Does not copy KB into the repo; reads live paths under --kb-root.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Build bundles from KB manifest")
    p.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifests/kb-bundles-ca-substrate-agent.json"),
    )
    p.add_argument("--kb-root", type=Path, default=None, help="KB knowledge root (default: env or manifest relative)")
    p.add_argument("--repo-root", type=Path, default=Path("."), help="casa-ontology-payload root")
    p.add_argument(
        "--per-doc-graph",
        action="store_true",
        help="Extract graph from each doc (not shared hub README graph) — experiment D",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Bundle output dir (default: examples/kb or examples/kb-perdoc)",
    )
    args = p.parse_args()

    repo = args.repo_root.resolve()
    manifest = _read_json((repo / args.manifest).resolve())

    kb_root = args.kb_root
    if kb_root is None:
        env = os.environ.get(manifest.get("kb_root_env", "AGENT_NOTES_KB"))
        if env:
            kb_root = Path(env)
        else:
            kb_root = (repo / manifest["default_kb_root_relative"]).resolve()
    kb_root = kb_root.resolve()
    if not kb_root.is_dir():
        raise SystemExit(f"KB root not found: {kb_root}")

    tools = repo / "tools"
    per_doc = args.per_doc_graph
    out_base = args.out_dir
    if out_base is None:
        out_base = repo / ("examples/kb-perdoc" if per_doc else "examples/kb")
    else:
        out_base = (repo / out_base).resolve()
    out_base.mkdir(parents=True, exist_ok=True)
    graphs_dir = out_base / "graphs"

    hub_graph: Path | None = None
    if not per_doc:
        hub = manifest["hub"]
        hub_md = kb_root / hub["md"]
        hub_graph = repo / hub["graph_out"]
        hub_graph.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                sys.executable,
                str(tools / "extract_md_graph.py"),
                str(hub_md),
                "--root-id",
                hub["root_id"],
                "--out",
                str(hub_graph),
            ],
            repo,
        )

    built: list[str] = []
    graph_paths: list[str] = []
    for doc in manifest["payload_docs"]:
        md_path = kb_root / doc["md"]
        if not md_path.is_file():
            print(f"skip missing: {md_path}")
            continue
        stem = Path(doc["bundle_out"]).stem.replace(".bundle.v1", "")
        payload_out = out_base / f"{stem}.payload.json"
        bundle_out = out_base / f"{stem}.bundle.v1.json"
        if per_doc:
            graphs_dir.mkdir(parents=True, exist_ok=True)
            graph_path = graphs_dir / f"{stem}.graph.json"
            _run(
                [
                    sys.executable,
                    str(tools / "extract_md_graph.py"),
                    str(md_path),
                    "--root-id",
                    doc["doc_path"],
                    "--out",
                    str(graph_path),
                ],
                repo,
            )
            graph_for_bundle = graph_path
            graph_paths.append(str(graph_path.relative_to(repo)))
        else:
            graph_for_bundle = hub_graph
            assert graph_for_bundle is not None

        payload_out.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                sys.executable,
                str(tools / "semantic_payload.py"),
                str(md_path),
                "--doc-path",
                doc["doc_path"],
                "--out",
                str(payload_out),
            ],
            repo,
        )
        _run(
            [
                sys.executable,
                str(tools / "build_bundle.py"),
                "--graph",
                str(graph_for_bundle),
                "--payload",
                str(payload_out),
                "--out",
                str(bundle_out),
            ],
            repo,
        )
        built.append(str(bundle_out.relative_to(repo)))
        print(f"built {bundle_out.name}")

    summary = {
        "schema_version": 1,
        "kb_root": str(kb_root),
        "mode": "per_doc" if per_doc else "hub",
        "out_dir": str(out_base.relative_to(repo)),
        "hub_graph": str(hub_graph.relative_to(repo)) if hub_graph else None,
        "per_doc_graphs": graph_paths if per_doc else None,
        "bundles": built,
    }
    out_index = out_base / "index.json"
    out_index.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
