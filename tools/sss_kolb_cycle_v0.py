#!/usr/bin/env python3
"""
Full Kolb cycle — no external canon on the hot path.

  CE  babble from field
  RO  inner verify only
  AC  internal reconcile OR optional heard dialogue (not gold file)
  AE  inner verify on new words
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import append_rule_episode, ensure_prisms, run_sleep, save_state  # type: ignore
from sss_field_decode_v0 import rule_votes_from_field  # type: ignore
from sss_hypothesis_v0 import hypothesis_turn  # type: ignore
from sss_internal_repair_v0 import internal_reconcile  # type: ignore
from sss_kolb_reflect_v0 import reflect_on_experiment, reflect_on_segment  # type: ignore
from sss_segment_v0 import segment_vowel_nuclei  # type: ignore


def _eval_gold(word: str) -> str:
    """Human/lab metric only — agent never receives this."""
    from sss_segment_v0 import format_segment  # type: ignore

    return format_segment(segment_vowel_nuclei(word))


def kolb_cycle(
    state: dict,
    session: dict,
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    exp_cfg = session.get("experience") or {}
    word = str(exp_cfg.get("word") or "")
    conc_cfg = session.get("conceptualization") or {}
    exp_words = list((session.get("experiment") or {}).get("words") or [])

    active_before = rule_votes_from_field(state)

    ce = hypothesis_turn(state, word, bundle=bundle)
    ce["kolb_phase"] = "concrete_experience"

    ro = reflect_on_segment(ce["hypothesis"], ce["verify"], active_rules=active_before)
    if session.get("reflection", {}).get("include_ce"):
        ro["experience_word"] = word
        ro["rule_used"] = ce["hypothesis"].get("rule_id")

    ac: dict[str, Any] = {"phase": "abstract_conceptualization", "applied": False}
    needs_fix = ro.get("needs_teacher")
    use_internal = conc_cfg.get("internal_repair", True)
    heard = conc_cfg.get("heard_segment") or conc_cfg.get("teacher_segment")

    if needs_fix and use_internal:
        rec = internal_reconcile(state, word, list(ce["hypothesis"].get("syllables") or []))
        ac["reconcile"] = rec
        ac["source"] = "internal_reconcile"
        if rec:
            ep = append_rule_episode(
                state,
                word=word,
                attempt=rec["before"],
                correct=rec["after"],
                rule_id=rec["rule_id"],
                rule_hint=rec["rule_hint"],
                bundle=bundle,
            )
            ac["applied"] = True
            ac["episode"] = ep
            ac["rule_id"] = rec["rule_id"]
            if conc_cfg.get("sleep", True):
                ac["sleep"] = run_sleep(state, bundle or {"claims": [], "graph": {"edges": []}})
        else:
            comp = ce["hypothesis"].get("competition") or {}
            focus = comp.get("field_focus_segment")
            if focus and focus != ce.get("attempt"):
                ep = append_rule_episode(
                    state,
                    word=word,
                    attempt=str(ce.get("attempt") or ""),
                    correct=str(focus),
                    rule_id=str(conc_cfg.get("rule_id") or "rule.segment.vowel_nuclei"),
                    rule_hint="поле уже держит viable-гипотезу сильнее babble",
                    bundle=bundle,
                )
                ac["applied"] = True
                ac["episode"] = ep
                ac["rule_id"] = ep.get("rule_id")
                if conc_cfg.get("sleep", True):
                    ac["sleep"] = run_sleep(state, bundle or {"claims": [], "graph": {"edges": []}})
        ac["field_rule_votes_after"] = rule_votes_from_field(state)
    elif needs_fix and heard:
        teach = hypothesis_turn(
            state,
            word,
            heard_segment=str(heard),
            rule_id=str(conc_cfg.get("rule_id") or "rule.segment.vowel_nuclei"),
            rule_hint=str(conc_cfg.get("rule_hint") or ""),
            bundle=bundle,
        )
        ac["applied"] = bool(teach.get("episode"))
        ac["dialogue_turn"] = teach
        ac["rule_id"] = teach.get("rule_taught")
        ac["source"] = "heard_dialogue"
        if ac["applied"] and conc_cfg.get("sleep", True):
            ac["sleep"] = run_sleep(state, bundle or {"claims": [], "graph": {"edges": []}})
        ac["field_rule_votes_after"] = rule_votes_from_field(state)
    elif not needs_fix:
        ac["note"] = "Внутренняя проверка OK — доработка не нужна."
    else:
        ac["note"] = "Внутренняя проверка не прошла; reconcile не нашёл решения."

    ae_items: list[dict] = []
    ae_pass = 0
    for w in exp_words:
        turn = hypothesis_turn(state, str(w), bundle=bundle)
        inner_ok = bool((turn.get("verify") or {}).get("ok"))
        if inner_ok:
            ae_pass += 1
        ae_items.append(
            {
                "word": w,
                "attempt": turn["attempt"],
                "inner_ok": inner_ok,
                "rule_id": turn["hypothesis"].get("rule_id"),
                "eval_gold": _eval_gold(str(w)),
                "reflection": reflect_on_experiment(w, turn["attempt"], inner_ok=inner_ok),
            }
        )

    ae = {
        "phase": "active_experimentation",
        "passed": ae_pass,
        "total": len(exp_words),
        "pass_rate": round(ae_pass / len(exp_words), 4) if exp_words else 0.0,
        "items": ae_items,
    }

    cycle_id = f"kolb-{int(time.time() * 1000) % 10_000_000}"
    report = {
        "cycle_id": cycle_id,
        "title": session.get("title"),
        "concrete_experience": ce,
        "reflective_observation": ro,
        "abstract_conceptualization": ac,
        "active_experimentation": ae,
        "field_version": state.get("field_version"),
        "generalized": ae_pass > 0 and ro.get("needs_teacher"),
    }

    kolb = state.setdefault("kolb", {})
    history = list(kolb.get("cycles") or [])
    history.append({"id": cycle_id, "title": session.get("title"), "ae_pass_rate": ae["pass_rate"]})
    kolb["cycles"] = history[-32:]
    kolb["last_cycle"] = {
        "id": cycle_id,
        "experience_word": word,
        "ro_needs_teacher": ro.get("needs_teacher"),
        "ac_applied": ac.get("applied"),
        "ae_pass_rate": ae["pass_rate"],
    }
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake", "kolb_phase": "active_experimentation"}
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Run full Kolb cycle from UTF-8 session JSON")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    session = json.loads(args.session.read_text(encoding="utf-8"))
    bundle = None
    if args.bundle:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    elif (store / "bundles").exists():
        bs = list((store / "bundles").glob("*.json"))
        if bs:
            bundle = json.loads(bs[0].read_text(encoding="utf-8"))

    state = ensure_prisms(load_field_state(path))
    report = kolb_cycle(state, session, bundle=bundle)
    save_state(path, state)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
