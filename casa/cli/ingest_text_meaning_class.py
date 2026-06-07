#!/usr/bin/env python3
"""Ingest B11 text-meaning class — practice moments + journal fixate (ADR-0053)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.passage import extract_passage_meaning
from casa.prisms.tick.semantic_read import route_kb_read

_CLASS = REPO_ROOT / "lessons/ru-text-comprehend"
_PLAN = _CLASS / "data/text-meaning-plan-v1.json"
_PROBE = REPO_ROOT / "lab/visual-curriculum/probe_text_meaning_ru.py"


def _store_dir(store_id: str) -> Path:
    return (REPO_ROOT / "agents" / store_id).resolve()


def run_moments(
    store: Path,
    *,
    plan_path: Path,
    stage_filter: str | None = None,
    dry_run: bool = False,
) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scenarios = [c for c in plan.get("scenarios") or [] if c.get("wired", True)]
    if stage_filter:
        scenarios = [c for c in scenarios if str(c.get("stage")) == stage_filter]

    moments: list[dict] = []
    with store_session_lock(store, holder="ingest:text-meaning"):
        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            q = str(case.get("query") or "").strip()
            if not q:
                continue
            intent = route_kb_read(q, bundle, store_dir=store).intent
            props = extract_passage_meaning(q, intent=intent, bundle=bundle, store_dir=store)
            prop_ids = [r.concept_id for r in props]
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            prov = meaning_provenance(ctx)
            row = {
                "scenario_id": case.get("scenario_id"),
                "stage": case.get("stage"),
                "query_intent": intent,
                "prop_ids": prop_ids,
                "reply_excerpt": reply[:200],
            }
            moments.append(row)
            if dry_run:
                continue

            append_partner_turn(
                store,
                q,
                provenance={"source": "ingest_text_meaning", "scenario_id": case.get("scenario_id"), **prov},
            )
            append_subject_turn(
                store,
                reply,
                kind="reply",
                provenance={"source": "ingest_text_meaning", "scenario_id": case.get("scenario_id"), **prov},
            )
            agent_remember(
                store,
                state,
                {
                    "kind": "note",
                    "text": reply,
                    "concepts": prop_ids,
                    "tags": ["B11", "text-meaning", str(case.get("stage") or "")],
                    "data": {
                        "scenario_id": case.get("scenario_id"),
                        "query": q[:500],
                        "query_intent": intent,
                        "prop_ids": prop_ids,
                    },
                    "test_cues": [q.split("\n\n")[-1][:120]],
                },
                scope="self",
            )

        if not dry_run and moments:
            mark_runtime_dirty(state)
            save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

    return {"moments": len(moments), "items": moments, "store_id": store.name}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    p.add_argument("--stage", default="", help="Only one stage id (extract, inference, …)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--probe", action="store_true", help="Run probe_text_meaning_ru after ingest")
    p.add_argument("--sync-life", action="store_true", help="Snapshot store to von-neumann-life-archive after ingest")
    args = p.parse_args()

    store = _store_dir(args.store)
    summary = run_moments(
        store,
        plan_path=args.plan,
        stage_filter=args.stage or None,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.probe and not args.dry_run:
        cmd = [sys.executable, str(_PROBE), "--store", args.store]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT))
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

    if args.sync_life and not args.dry_run:
        sync = REPO_ROOT / "tools/sync_life_archive.py"
        if sync.is_file():
            proc = subprocess.run(
                [sys.executable, str(sync), "snapshot", "--store-dir", str(store)],
                cwd=str(REPO_ROOT),
            )
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
