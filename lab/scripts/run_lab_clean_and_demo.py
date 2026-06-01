#!/usr/bin/env python3
"""Clean lab journal smoke, run math curriculum + predict demo, collect agent outputs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.memory.agent_journal import journal_stats, search_journal_entries
from casa.prisms.memory.agent_memory_ops import agent_recall
from casa.prisms.control.fpn_state import load_session
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, prism_hippo
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import (
    STORE_LANGUAGE_AGENT_LAB,
    STORE_RU_GENERAL_V0,
    agent_store_dir,
    field_state_path,
    journal_root,
    math_l0_lab_store,
)
from casa.prisms.tick.orchestrator import LearningTickConfig, run_learning_tick
from casa.prisms.tick.predict_tick import predict_tick

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
REPORT = REPO_ROOT / "lab/reports/lab-clean-demo.json"

_PREDICT_CUES: list[tuple[str, str | None, str]] = [
    ("| + | = ||", "math.op.add", "sticks add"),
    ("|| + ||", "math.op.add", "add infix"),
    ("||| - || = |", "math.op.sub", "sticks sub eq"),
    ("||| - ||", "math.op.sub", "sub infix"),
    ("2 + 2 = 4", "math.op.add", "numeric add"),
    ("III - II = I", "math.op.sub", "roman sub"),
    ("14", "math.num.fourteen", "teen numeral"),
    ("21", "math.num.twenty_one", "skip pattern"),
]

_PROBE_QUERIES = ["14", "6", "8", "21"]


def _tick_autonomous_retain(store: Path) -> list[dict[str, Any]]:
    wm = load_session(store)
    cfg = LearningTickConfig(act_rollout=False, retain_on_verified_predict=True)
    history: list[dict[str, Any]] = []
    state: dict | None = None
    for q in _PROBE_QUERIES:
        row, wm, state = run_learning_tick(store_dir=store, user_query=q, wm=wm, config=cfg)
        history.append({"query": q, "agent_retain": row.get("agent_retain")})
    if state is not None:
        from casa.prisms.shared.store_persist import save_runtime_state

        save_runtime_state(store, state)
    return history


def _store(name: str) -> Path:
    return agent_store_dir(name, root=REPO_ROOT)


def clean_lab_journals() -> dict[str, Any]:
    """Remove dev smoke from lab journals."""
    out: dict[str, Any] = {"removed": []}
    for name in (STORE_RU_GENERAL_V0, STORE_LANGUAGE_AGENT_LAB):
        j = journal_root(_store(name))
        if j.is_dir():
            shutil.rmtree(j)
            out["removed"].append(str(j.relative_to(REPO_ROOT)))
    mj = journal_root(math_l0_lab_store(root=REPO_ROOT))
    if mj.is_dir():
        shutil.rmtree(mj)
        out["removed"].append(str(mj.relative_to(REPO_ROOT)))
    return out


def _predict_row(state: dict, bundle: dict, cue: str, expect: str | None, label: str) -> dict[str, Any]:
    tick = predict_tick(state, cue, modality="schema", expect=expect, bundle=bundle)
    pred = tick.get("predict") or {}
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    return {
        "label": label,
        "cue": cue,
        "expect": expect,
        "verdict": tick.get("verdict"),
        "hypothesis": pred.get("hypothesis"),
        "unbound": pred.get("unbound_operators"),
        "top3": rank_cue_on_f0(dec, cue)[:3],
    }


def _probe_predict(state: dict, bundle: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for q in _PROBE_QUERIES:
        tick = predict_tick(state, q, modality="schema", bundle=bundle)
        pred = tick.get("predict") or {}
        rows.append(
            {
                "query": q,
                "verdict": tick.get("verdict"),
                "hypothesis": pred.get("hypothesis"),
                "unbound": pred.get("unbound_operators"),
            }
        )
    return rows


def run_demo(*, fresh: bool = True) -> dict[str, Any]:
    clean = clean_lab_journals()

    cmd = [sys.executable, str(REPO_ROOT / "lab/scripts/run_math_curriculum.py")]
    if fresh:
        cmd.append("--fresh")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    curriculum = json.loads(proc.stdout)

    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    store = math_l0_lab_store(root=REPO_ROOT)
    state = ensure_prisms(load_field_state(field_state_path(store)))

    predict = [_predict_row(state, bundle, cue, exp, label) for cue, exp, label in _PREDICT_CUES]
    probes = _probe_predict(state, bundle)
    tick_retains = _tick_autonomous_retain(store)
    journal_rows = search_journal_entries(store, limit=200)
    confirmed = agent_recall(store, draft=True, scope="*")
    hippo = prism_hippo(state)

    report: dict[str, Any] = {
        "clean": clean,
        "curriculum": curriculum,
        "predict_after_curriculum": predict,
        "free_probe_predict": probes,
        "tick_autonomous_retain": tick_retains,
        "journal_confirmed_recall": confirmed,
        "journal": {
            "stats": journal_stats(store),
            "entries": [{k: v for k, v in r.items() if k != "_domain"} for r in journal_rows],
        },
        "hippo_pending": [
            {
                "id": e.get("id"),
                "cue": e.get("cue"),
                "concept_id": e.get("concept_id"),
                "consolidated": e.get("consolidated"),
            }
            for e in (hippo.get("episodes") or [])
            if not e.get("consolidated")
        ][-6:],
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Clean lab journals + math curriculum demo")
    p.add_argument("--no-fresh", action="store_true", help="Skip math-l0-lab re-init")
    p.add_argument("--clean-only", action="store_true")
    args = p.parse_args()

    if args.clean_only:
        print(json.dumps(clean_lab_journals(), ensure_ascii=False, indent=2))
        return

    print(json.dumps(run_demo(fresh=not args.no_fresh), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
