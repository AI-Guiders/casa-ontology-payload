#!/usr/bin/env python3
"""Hypothesis → internal verify → reconcile or heard dialogue → sleep."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import append_rule_episode, ensure_prisms, run_sleep, save_state  # type: ignore
from sss_internal_repair_v0 import internal_reconcile  # type: ignore
from sss_segment_v0 import format_segment, parse_segment, segment_hypothesis, verify_segment  # type: ignore


def parse_heard_segment(text: str) -> list[str] | None:
    """Partner utterance like «встре-ча» or «встре|ча» — dialogue, not canon file."""
    t = (text or "").strip()
    if not t:
        return None
    if "|" in t:
        return parse_segment(t)
    if "-" in t:
        return [p.strip() for p in t.split("-") if p.strip()]
    if re.search(r"\s+", t):
        return [p for p in re.split(r"\s+", t) if p]
    return None


def hypothesis_turn(
    state: dict,
    word: str,
    *,
    heard_segment: str | None = None,
    teacher_segment: str | None = None,
    rule_id: str | None = None,
    rule_hint: str | None = None,
    internal_repair: bool = False,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Segment from field; optional dialogue input or internal reconcile — no gold lookup."""
    state = ensure_prisms(state)
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake", "active_prism": "prism_memory"}

    hyp = segment_hypothesis(state, word)
    ver = verify_segment(hyp)
    attempt = format_segment(hyp["syllables"])

    report: dict[str, Any] = {
        "word": word,
        "hypothesis": hyp,
        "verify": ver,
        "attempt": attempt,
        "matched": ver["ok"],
        "episode": None,
        "rule_taught": None,
        "heard_segment": None,
        "teacher_segment": None,
        "reconcile": None,
    }

    dialogue = heard_segment or teacher_segment
    if dialogue:
        heard = parse_heard_segment(dialogue)
        report["heard_segment"] = format_segment(heard) if heard else dialogue
        report["teacher_segment"] = report["heard_segment"]
        if heard and heard != hyp["syllables"]:
            rid = rule_id or "rule.segment.vowel_nuclei"
            ep = append_rule_episode(
                state,
                word=word,
                attempt=attempt,
                correct=format_segment(heard),
                rule_id=rid,
                rule_hint=rule_hint or "услышал от собеседника",
                bundle=bundle,
            )
            report["episode"] = ep
            report["rule_taught"] = rid
            report["matched"] = False
    elif internal_repair and not ver["ok"]:
        rec = internal_reconcile(state, word, hyp["syllables"])
        report["reconcile"] = rec
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
            report["episode"] = ep
            report["rule_taught"] = rec["rule_id"]
            report["matched"] = True

    report["hippo_pending"] = len(prism_hippo(state)["episodes"])
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--word", required=True)
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--heard-segment", default=None, help="dialogue: встре-ча")
    p.add_argument("--teacher-segment", default=None, help="deprecated alias for --heard-segment")
    p.add_argument("--internal-repair", action="store_true")
    p.add_argument("--rule-id", default="rule.segment.vowel_nuclei")
    p.add_argument("--rule-hint", default=None)
    p.add_argument("--sleep", action="store_true")
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    bundle = None
    if args.bundle:
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    elif (store / "bundles").exists():
        bs = list((store / "bundles").glob("*.json"))
        if bs:
            bundle = json.loads(bs[0].read_text(encoding="utf-8"))

    state = load_field_state(path)
    report = hypothesis_turn(
        state,
        args.word,
        heard_segment=args.heard_segment or args.teacher_segment,
        rule_id=args.rule_id,
        rule_hint=args.rule_hint,
        internal_repair=args.internal_repair,
        bundle=bundle,
    )
    if args.sleep:
        report["sleep"] = run_sleep(state, bundle or {"claims": [], "graph": {"edges": []}})
    save_state(path, state)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
