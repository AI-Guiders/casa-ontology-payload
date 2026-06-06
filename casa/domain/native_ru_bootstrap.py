#!/usr/bin/env python3
"""Seed von-neumann store for nositel′ v0 dialogue + whole-word routes (ADR-0049)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.domain.emergent_promote import _safe_promote_capability, agent_id_from_state
from casa.domain.plan_tick import promote_applicability_route
from casa.prisms.memory.agent_journal import append_journal_entry
from casa.prisms.shared.store_persist import load_runtime_state, save_runtime_state


def _confirmed_privet_entry() -> dict[str, Any]:
    return {
        "kind": "hypothesis",
        "text": "«привет» — целое слово lang.word.привет; ru.dialog.greeting для приветствия.",
        "concepts": ["lang.word.привет", "ru.dialog.greeting"],
        "tags": ["native-bootstrap", "lexicon", "dialogue"],
        "meta": {
            "status": "confirmed",
            "test_cues": ["Привет", "привет", "Привет!"],
            "notebook": "self",
            "scope": "self",
        },
    }


def seed_native_ru_journal(store_dir: Path) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    row = append_journal_entry(store_dir, _confirmed_privet_entry(), domain="self")
    return {"journal_id": row.get("id"), "concepts": ["lang.word.привет", "ru.dialog.greeting"]}


def seed_native_ru_routes(state: dict) -> list[dict[str, Any]]:
    agent_id = agent_id_from_state(state)
    promoted: list[dict[str, Any]] = []

    whole = _safe_promote_capability(
        state,
        match={"modality": "vis", "surface_class": "word", "novel": "false", "locale": "ru"},
        target_skill="skill.read.whole",
        gate="native-bootstrap:whole",
        agent_id=agent_id,
    )
    if whole:
        promoted.append(whole)

    t9_whole = _safe_promote_capability(
        state,
        match={"modality": "t9", "surface_class": "word", "novel": "false", "locale": "ru"},
        target_skill="skill.read.whole",
        gate="native-bootstrap:whole-t9",
        agent_id=agent_id,
    )
    if t9_whole:
        promoted.append(t9_whole)

    oov = _safe_promote_capability(
        state,
        match={"modality": "vis", "surface_class": "word", "novel": "true", "locale": "ru"},
        target_skill="skill.read.analytic",
        gate="native-bootstrap:analytic",
        agent_id=agent_id,
    )
    if oov:
        promoted.append(oov)

    plan = promote_applicability_route(
        state,
        match={"goal": "goal.read.word", "locale": "ru"},
        target_plan=f"plan.whole_read_{agent_id}",
        steps=["skill.read.whole", "skill.verify.lex"],
        gate="native-bootstrap:read-plan",
        agent_id=agent_id,
    )
    if plan:
        promoted.append(plan)

    return promoted


def bootstrap_native_ru_store(store_dir: Path, *, journal: bool = True, routes: bool = True) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    rep: dict[str, Any] = {"store": str(store_dir), "journal": None, "routes": []}

    if journal:
        rep["journal"] = seed_native_ru_journal(store_dir)

    if routes:
        state = load_runtime_state(store_dir)
        if state is None:
            state = {"field_version": 0, "store": {"store_id": store_dir.name}}
        rep["routes"] = seed_native_ru_routes(state)
        save_runtime_state(store_dir, state, force=True, sync_ltm_on_save=False)

    return rep


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument("--no-journal", action="store_true")
    p.add_argument("--no-routes", action="store_true")
    args = p.parse_args()
    rep = bootstrap_native_ru_store(
        args.store_dir,
        journal=not args.no_journal,
        routes=not args.no_routes,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
