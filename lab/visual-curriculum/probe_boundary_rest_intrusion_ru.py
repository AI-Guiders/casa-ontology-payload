#!/usr/bin/env python3
"""RU boundary gate — rest-check intrusion + dismissed boundary (ADR-0077, 0078)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = (
    Path(__file__).resolve().parents[2]
    / "lessons/ru-text-tract/data/boundary-rest-intrusion-plan-v1.json"
)
_PROBE = "probe_boundary_rest_intrusion_ru"
_STAGE = "stage-21c-boundary-rest-intrusion-ru"


def _seed_prior_turns(store: Path, turns: list[dict[str, Any]]) -> None:
    from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn

    for turn in turns:
        speaker = str(turn.get("speaker") or "")
        text = str(turn.get("text") or "")
        if not text:
            continue
        if speaker == "partner":
            append_partner_turn(store, text)
        elif speaker == "subject":
            append_subject_turn(store, text, kind=str(turn.get("kind") or "reply"))


def _run_case(
    case: dict[str, Any],
    *,
    store: Path,
    state: dict,
    wm,
) -> tuple[bool, dict[str, Any], str]:
    from casa.domain.boundary_compose import (
        compose_boundary_partner_reply_with_ctx,
        disposition_situation_tag,
        reply_has_internal_leak,
    )
    from casa.domain.boundary_situations import duck_passes, resolve_boundary_situation
    from casa.domain.partner_voice import partner_voice_invariant_violations
    from casa.domain.subject_agency import SubjectAction, SubjectDisposition

    _seed_prior_turns(store, list(case.get("prior_turns") or []))

    disp_raw = dict(case.get("disposition") or {})
    disp = SubjectDisposition(
        SubjectAction(str(disp_raw.get("action") or "defer")),
        str(disp_raw.get("reason") or ""),
    )
    partner = str(case.get("partner") or "")
    expect_sid = str(case.get("expect_situation") or "")

    _ctx, reply = compose_boundary_partner_reply_with_ctx(
        partner,
        disp,
        None,
        state,
        wm,
        store_dir=store,
    )
    reply = (reply or "").strip()
    resolved = resolve_boundary_situation(partner, disp.reason)
    tag = disposition_situation_tag(disp.reason)

    ok = bool(reply)
    ok = ok and not reply_has_internal_leak(reply)
    ok = ok and duck_passes(reply, expect_sid)
    ok = ok and resolved == expect_sid
    ok = ok and tag == expect_sid

    for sub in case.get("expect_substrings") or []:
        if str(sub).lower() not in reply.lower():
            ok = False
    for bad in case.get("must_not_contain") or []:
        if str(bad).lower() in reply.lower():
            ok = False

    is_decline = disp.action in (SubjectAction.DEFER, SubjectAction.REFUSE)
    invariant_violations = partner_voice_invariant_violations(reply, is_decline=is_decline)
    if invariant_violations:
        ok = False

    detail = {
        "boundary_situation": expect_sid,
        "resolved_situation": resolved,
        "disposition_tag": tag,
        "duck_pass": duck_passes(reply, expect_sid),
        "internal_leak": reply_has_internal_leak(reply),
        "partner_voice_violations": invariant_violations,
    }
    return ok, detail, reply


def main() -> None:
    setup_probe_imports()
    from casa.domain.boundary_situations import seed_boundary_curriculum
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_lock import store_session_lock

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    p.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip curriculum seed (store already has boundary.rest_* episodes)",
    )
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)
    seed_ids = [
        "boundary.rest_check_intrusion",
        "boundary.dismissed_rest_boundary",
    ]

    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    total = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        if not args.no_seed:
            seed_boundary_curriculum(store, seed_ids, include_material_kb=True)

        wm = WorkingMemory(tick=21)
        for case in scenarios:
            if not case.get("wired", True):
                continue
            total += 1
            ok, detail, reply = _run_case(case, store=store, state=state, wm=wm)
            if ok:
                know += 1
            items.append(
                {
                    "scenario_id": case.get("scenario_id"),
                    "stage": case.get("stage") or _STAGE,
                    "verdict": "know" if ok else "wrong",
                    "partner": case.get("partner"),
                    "reply": reply,
                    "reply_excerpt": reply[:360],
                    "wired": True,
                    **detail,
                }
            )

        ratio = (know / total) if total else 0.0
        gate_pass = total > 0 and ratio >= min_ratio and know == total
        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "stage": _STAGE,
            "class_id": "ru-text-tract",
            "plan": str(args.plan),
            "seeded_situations": [] if args.no_seed else seed_ids,
            "know": know,
            "total": total,
            "pass_ratio": round(ratio, 3),
            "min_pass_ratio": min_ratio,
            "items": items,
            "gate_pass": gate_pass,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-boundary-rest-intrusion-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for case, item in zip(scenarios, items, strict=False):
        if not case.get("wired", True):
            continue
        print("\n=== Boundary:", case.get("scenario_id"), "|", item.get("verdict"), "===\n")
        for prior in case.get("prior_turns") or []:
            who = "Партнёр" if prior.get("speaker") == "partner" else "Нейманн"
            print(f"{who}: {prior.get('text')}")
        print(f"Партнёр: {case.get('partner')}")
        print(f"\nНейманн: {item.get('reply') or item.get('reply_excerpt')}")
        print(
            f"\n[situation={item.get('boundary_situation')} duck={item.get('duck_pass')} "
            f"leak={item.get('internal_leak')} pv={item.get('partner_voice_violations')}]"
        )

    print(
        json.dumps(
            {
                "probe": _PROBE,
                "gate_pass": report.get("gate_pass"),
                "know": know,
                "total": total,
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
