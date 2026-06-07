#!/usr/bin/env python3
"""Shared teacher ingest for verbal moment plans (RU-α, RU-ε)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.semantic_read import route_kb_read


def _reply_excerpt(reply: str, limit: int = 200) -> str:
    text = str(reply or "").strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return f"{cut}…"


def run_verbal_moment_plan(
    store: Path,
    *,
    plan_path: Path,
    source: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ingest train scenarios: journal remember → partner recall → subject reply."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scenarios = [c for c in plan.get("scenarios") or [] if c.get("wired", True)]
    moments: list[dict[str, Any]] = []

    with store_session_lock(store, holder=f"ingest:{source}"):
        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            remember_text = str(case.get("remember_text") or "").strip()
            recall_q = str(case.get("recall_query") or "").strip()
            if not recall_q:
                continue

            concepts = list(case.get("concepts") or [])
            tags = list(case.get("tags") or [source])
            sid = str(case.get("scenario_id") or "")

            if remember_text and not dry_run:
                agent_remember(
                    store,
                    state,
                    {
                        "kind": "observation",
                        "text": remember_text,
                        "concepts": concepts,
                        "tags": tags + ["ingest"],
                        "data": {"scenario_id": sid, "phase": "remember"},
                    },
                    scope="self",
                )

            intent = route_kb_read(recall_q, bundle, store_dir=store).intent
            ctx = gather_subject_dialogue_blocks(recall_q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(recall_q, ctx)

            row = {
                "scenario_id": sid,
                "stage": case.get("stage"),
                "query_intent": intent,
                "reply_excerpt": _reply_excerpt(reply),
            }
            moments.append(row)

            if dry_run:
                continue

            append_partner_turn(
                store,
                recall_q,
                provenance={"source": source, "scenario_id": sid, "phase": "recall"},
            )
            append_subject_turn(
                store,
                reply,
                kind="reply",
                provenance={"source": source, "scenario_id": sid, "phase": "reply"},
            )
            if reply.strip():
                agent_remember(
                    store,
                    state,
                    {
                        "kind": "note",
                        "text": reply,
                        "concepts": concepts,
                        "tags": tags + ["ingest", "articulate"],
                        "data": {
                            "scenario_id": sid,
                            "query": recall_q[:500],
                            "query_intent": intent,
                            "remember_text": remember_text[:500],
                        },
                        "test_cues": [recall_q[:120]],
                    },
                    scope="self",
                )

        if not dry_run and moments:
            mark_runtime_dirty(state)
            save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

    return {
        "source": source,
        "plan": str(plan_path),
        "moments": len(moments),
        "items": moments,
        "store_id": store.name,
    }
