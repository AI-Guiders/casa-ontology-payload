#!/usr/bin/env python3
"""
KB → bundle sync: build bundle from live Markdown, optionally import to agent store.

Wraps extract_md_graph + semantic_payload + build_bundle; adds --import-to for field write.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

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


def _mod_run(module: str, args: list[str], cwd: Path) -> None:
    """Invoke a casa.cli module in a subprocess (replaces the deleted tools/*.py shims)."""
    _run([sys.executable, "-m", "casa.cli", module, *args], cwd)


def _resolve_kb_root(repo: Path, manifest_path: Path | None, kb_root: Path | None) -> Path:
    if kb_root is not None:
        root = kb_root.resolve()
        if not root.is_dir():
            raise SystemExit(f"KB root not found: {root}")
        return root
    if manifest_path and manifest_path.is_file():
        manifest = _read_json(manifest_path)
        env = os.environ.get(manifest.get("kb_root_env", "AGENT_NOTES_KB"))
        if env:
            root = Path(env).resolve()
            if root.is_dir():
                return root
        rel = manifest.get("default_kb_root_relative")
        if rel:
            root = (repo / rel).resolve()
            if root.is_dir():
                return root
    raise SystemExit("KB root not found: pass --kb-root or set AGENT_NOTES_KB")


def _manifest_docs(manifest: dict) -> list[dict]:
    return list(manifest.get("payload_docs") or manifest.get("documents") or [])


def _doc_entry_from_manifest(manifest: dict, doc_stem: str) -> dict | None:
    for doc in _manifest_docs(manifest):
        stem = Path(str(doc.get("md", ""))).stem
        if stem == doc_stem or doc.get("bundle_stem") == doc_stem:
            return doc
    return None


def perdoc_bundle_path(repo: Path, md_rel: str) -> Path:
    stem = Path(md_rel).stem
    return repo / "lab/kb-perdoc" / f"{stem}.bundle.v1.json"


def sync_and_import(
    *,
    repo: Path,
    kb_root: Path,
    md_rel: str,
    doc_path: str,
    store_dir: Path,
    agent_card: Path,
    tier: str = "easy",
    bench: bool = False,
    out_bundle: Path | None = None,
) -> dict:
    """Build bundle from md and import to agent store (used by kb_sync CLI and watcher)."""
    out = out_bundle or perdoc_bundle_path(repo, md_rel)
    graphs_dir = out.parent / "graphs"
    bundle_path = build_one(
        repo=repo,
        kb_root=kb_root,
        md_rel=md_rel,
        doc_path=doc_path,
        out_bundle=out.resolve(),
        per_doc_graph=True,
        graphs_dir=graphs_dir,
    )
    bundle = _read_json(bundle_path)
    delta_path = store_dir.resolve() / "_kb_sync_delta.json"
    rel = bundle_path.relative_to(repo)
    delta = _write_inline_delta(rel, bundle, tier=tier)
    delta["bundle"]["path"] = str(rel).replace("\\", "/")
    delta_path.parent.mkdir(parents=True, exist_ok=True)
    delta_path.write_text(json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8")
    args = [
        "--delta",
        str(delta_path),
        "--store-dir",
        str(store_dir.resolve()),
        "--agent-card",
        str(agent_card.resolve()),
    ]
    if bench:
        args.append("--bench")
    _mod_run("import_knowledge_delta", args, repo)
    return {
        "bundle": str(bundle_path),
        "kb_root": str(kb_root),
        "doc_path": doc_path,
        "import": str(store_dir.resolve()),
        "field_state": str(store_dir.resolve() / "field_state.json"),
    }


def build_one(
    *,
    repo: Path,
    kb_root: Path,
    md_rel: str,
    doc_path: str | None,
    out_bundle: Path,
    per_doc_graph: bool,
    graphs_dir: Path,
) -> Path:
    md_abs = kb_root / md_rel.replace("/", os.sep)
    if not md_abs.is_file():
        raise SystemExit(f"Markdown not found: {md_abs}")

    doc_path = doc_path or md_rel.replace("\\", "/")
    stem = Path(md_rel).stem
    graph_out = graphs_dir / f"{stem}.graph.json" if per_doc_graph else None

    if per_doc_graph:
        graphs_dir.mkdir(parents=True, exist_ok=True)
        _mod_run(
            "extract_md_graph",
            [str(md_abs), "--root-id", doc_path, "--out", str(graph_out)],
            repo,
        )
        graph_path = graph_out
    else:
        raise SystemExit("hub graph mode requires --manifest with hub; use --per-doc-graph for single doc")

    payload_out = out_bundle.parent / f"{stem}.payload.json"
    _mod_run(
        "semantic_payload",
        [str(md_abs), "--doc-path", doc_path, "--out", str(payload_out)],
        repo,
    )

    out_bundle.parent.mkdir(parents=True, exist_ok=True)
    _mod_run(
        "build_bundle",
        ["--graph", str(graph_path), "--payload", str(payload_out), "--out", str(out_bundle)],
        repo,
    )
    return out_bundle


def _write_inline_delta(bundle_path: Path, bundle: dict, *, tier: str = "easy") -> dict:
    name = bundle_path.name
    cids = sorted({c.get("concept_id") for c in bundle.get("claims", []) if c.get("concept_id")})
    return {
        "schema_version": 1,
        "type": "knowledge_delta",
        "source_agent_id": "kb-sync",
        "target_cluster": "research",
        "bundle": {"path": str(bundle_path.as_posix()), "action": "replace"},
        "digest": {
            "summary": f"kb_sync {name}",
            "added_concept_ids": cids,
            "tier": tier,
        },
        "provides": [name],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Sync KB Markdown → bundle (+ optional field import)")
    p.add_argument("--kb-root", type=Path, default=None)
    p.add_argument("--manifest", type=Path, default=Path("manifests/kb-bundles-ca-substrate-agent.json"))
    p.add_argument("--doc", default=None, help="Document stem (e.g. research-ml-ca-substrate-agent)")
    p.add_argument("--md", type=Path, default=None, help="Absolute or kb-relative md path")
    p.add_argument("--doc-path", default=None, help="Knowledge-relative doc_path for claims")
    p.add_argument("--out", type=Path, default=None, help="Output bundle path")
    p.add_argument("--per-doc-graph", action="store_true", help="Extract graph per doc (default for kb_sync)")
    p.add_argument("--import-to", type=Path, default=None, help="Agent store dir → run import_knowledge_delta")
    p.add_argument("--store-dir", type=Path, default=None, help="Alias for --import-to")
    p.add_argument("--agent-card", type=Path, default=Path("lab/agent-cards/research-agent.json"))
    p.add_argument("--tier", default="easy", choices=("easy", "hard"))
    p.add_argument("--bench", action="store_true")
    args = p.parse_args()

    repo = Path.cwd().resolve()
    manifest_path = (repo / args.manifest).resolve() if args.manifest else None
    kb_root = _resolve_kb_root(repo, manifest_path, args.kb_root)

    if args.md is not None:
        md = args.md
        if not md.is_file():
            md = kb_root / str(args.md).replace("/", os.sep)
        md_rel = str(md.relative_to(kb_root)).replace("\\", "/") if md.is_relative_to(kb_root) else str(args.md)
        doc_path = args.doc_path or md_rel
        stem = Path(md_rel).stem
        out = args.out or (repo / "lab/kb-perdoc" / f"{stem}.bundle.v1.json")
    elif args.doc and manifest_path and manifest_path.is_file():
        manifest = _read_json(manifest_path)
        entry = _doc_entry_from_manifest(manifest, args.doc)
        if not entry:
            raise SystemExit(f"doc not in manifest: {args.doc}")
        md_rel = str(entry["md"])
        doc_path = entry.get("doc_path") or md_rel
        stem = Path(md_rel).stem
        out = args.out or (repo / "lab/kb-perdoc" / f"{stem}.bundle.v1.json")
    else:
        raise SystemExit("pass --md or --doc (with --manifest)")

    store = args.import_to or args.store_dir
    if store is not None:
        report = sync_and_import(
            repo=repo,
            kb_root=kb_root,
            md_rel=md_rel,
            doc_path=doc_path,
            store_dir=store,
            agent_card=(repo / args.agent_card).resolve(),
            tier=args.tier,
            bench=args.bench,
            out_bundle=out.resolve(),
        )
    else:
        graphs_dir = out.parent / "graphs"
        bundle_path = build_one(
            repo=repo,
            kb_root=kb_root,
            md_rel=md_rel,
            doc_path=doc_path,
            out_bundle=out.resolve(),
            per_doc_graph=args.per_doc_graph or True,
            graphs_dir=graphs_dir,
        )
        report = {"bundle": str(bundle_path), "kb_root": str(kb_root), "doc_path": doc_path}

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
