#!/usr/bin/env python3
"""
Watch KB Markdown (manifest payload_docs) and sync → import on change.

stdlib only: poll mtimes + debounce. No PyTorch on watch path.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from kb_sync import (  # type: ignore
    _manifest_docs,
    _read_json,
    _resolve_kb_root,
    sync_and_import,
)


def _md_watch_paths(manifest: dict, kb_root: Path) -> dict[Path, dict]:
    """Absolute md path → manifest entry."""
    out: dict[Path, dict] = {}
    for doc in _manifest_docs(manifest):
        md_rel = str(doc.get("md", "")).replace("\\", "/")
        if not md_rel:
            continue
        abs_path = (kb_root / md_rel.replace("/", os.sep)).resolve()
        out[abs_path] = doc
    return out


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _sync_one(
    *,
    repo: Path,
    kb_root: Path,
    doc: dict,
    store_dir: Path,
    agent_card: Path,
    tier: str,
    log_path: Path,
) -> dict:
    md_rel = str(doc["md"]).replace("\\", "/")
    doc_path = str(doc.get("doc_path") or md_rel)
    report = sync_and_import(
        repo=repo,
        kb_root=kb_root,
        md_rel=md_rel,
        doc_path=doc_path,
        store_dir=store_dir,
        agent_card=agent_card,
        tier=tier,
    )
    report["watcher"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "md": md_rel,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


def run_once(
    *,
    repo: Path,
    kb_root: Path,
    manifest: dict,
    store_dir: Path,
    agent_card: Path,
    tier: str,
    log_path: Path,
) -> list[dict]:
    reports: list[dict] = []
    for doc in _manifest_docs(manifest):
        md_rel = str(doc["md"]).replace("\\", "/")
        md_abs = kb_root / md_rel.replace("/", os.sep)
        if not md_abs.is_file():
            continue
        reports.append(
            _sync_one(
                repo=repo,
                kb_root=kb_root,
                doc=doc,
                store_dir=store_dir,
                agent_card=agent_card,
                tier=tier,
                log_path=log_path,
            )
        )
    return reports


def run_watch(
    *,
    repo: Path,
    kb_root: Path,
    manifest: dict,
    store_dir: Path,
    agent_card: Path,
    tier: str,
    poll_s: float,
    debounce_s: float,
    log_path: Path,
) -> None:
    watch = _md_watch_paths(manifest, kb_root)
    last_seen: dict[Path, float] = {p: _mtime(p) for p in watch}
    pending_at: dict[Path, float] = {}

    print(json.dumps({"watching": len(watch), "kb_root": str(kb_root), "store": str(store_dir)}, indent=2))

    while True:
        now = time.monotonic()
        for path, doc in watch.items():
            if not path.is_file():
                continue
            mt = _mtime(path)
            prev = last_seen.get(path, 0.0)
            if mt > prev + 1e-6:
                last_seen[path] = mt
                pending_at[path] = now

        ready = [p for p, t0 in list(pending_at.items()) if now - t0 >= debounce_s]
        for path in ready:
            pending_at.pop(path, None)
            doc = watch[path]
            try:
                report = _sync_one(
                    repo=repo,
                    kb_root=kb_root,
                    doc=doc,
                    store_dir=store_dir,
                    agent_card=agent_card,
                    tier=tier,
                    log_path=log_path,
                )
                print(json.dumps(report, ensure_ascii=False))
            except Exception as ex:
                err = {"error": str(ex), "md": doc.get("md")}
                print(json.dumps(err, ensure_ascii=False))
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")

        time.sleep(poll_s)


def main() -> None:
    p = argparse.ArgumentParser(description="Watch KB md → kb_sync → import_knowledge_delta")
    p.add_argument("--manifest", type=Path, default=Path("manifests/kb-bundles-ca-substrate-agent.json"))
    p.add_argument("--kb-root", type=Path, default=None)
    p.add_argument("--store-dir", type=Path, default=Path("examples/agent-stores/research-agent-lab-v0"))
    p.add_argument("--agent-card", type=Path, default=Path("examples/agent-cards/research-agent.v0.json"))
    p.add_argument("--tier", default="easy", choices=("easy", "hard"))
    p.add_argument("--poll", type=float, default=2.0, help="Poll interval seconds")
    p.add_argument("--debounce", type=float, default=1.5, help="Debounce after mtime change")
    p.add_argument("--once", action="store_true", help="Sync all manifest docs once and exit")
    p.add_argument("--log", type=Path, default=None, help="NDJSON log (default: store/watcher_log.ndjson)")
    args = p.parse_args()

    repo = Path.cwd().resolve()
    manifest_path = (repo / args.manifest).resolve()
    manifest = _read_json(manifest_path)
    kb_root = _resolve_kb_root(repo, manifest_path, args.kb_root)
    store = args.store_dir.resolve()
    agent_card = (repo / args.agent_card).resolve()
    log_path = args.log or (store / "watcher_log.ndjson")

    if args.once:
        reports = run_once(
            repo=repo,
            kb_root=kb_root,
            manifest=manifest,
            store_dir=store,
            agent_card=agent_card,
            tier=args.tier,
            log_path=log_path,
        )
        print(json.dumps({"synced": len(reports), "log": str(log_path)}, indent=2))
        return

    run_watch(
        repo=repo,
        kb_root=kb_root,
        manifest=manifest,
        store_dir=store,
        agent_card=agent_card,
        tier=args.tier,
        poll_s=args.poll,
        debounce_s=args.debounce,
        log_path=log_path,
    )


if __name__ == "__main__":
    main()
