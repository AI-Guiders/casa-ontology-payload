#!/usr/bin/env python3
"""Nositel′ gate — strict pedagogical acceptance (meaning + natural Russian)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = (
    Path(__file__).resolve().parents[2]
    / "lessons/ru-text-tract/data/nositel-acceptance-plan.json"
)
_PROBE = "probe_nositel_acceptance_ru"

_DEV_JARGON = (
    "bind",
    "paste claim",
    "ingest/practice",
    "kb,",
    " slots",
    "llm",
    "partial",
    "field_version",
    "не paste",
    "опираюсь на поле",
    "уверен частично",
)
_DEFER_MARKERS = (
    "нет уверенного bind",
    "слышу:",
    "нужен ingest",
    "не подменяю зашитым",
)
_EXPLAIN_GLOSS_MARKERS = ("—", "это ", "значит", "слово", "приветств", "союз", "формул")


def _reply_body(reply: str) -> str:
    body = reply.strip()
    for marker in (" (опираюсь", " (уверен", " (bind "):
        if marker in body:
            body = body.split(marker, 1)[0].strip()
    return body


def _sentence_count(text: str) -> int:
    body = _reply_body(text)
    parts = [p for p in re.split(r"[.!?]+", body) if p.strip()]
    return len(parts)


def _has_dev_jargon(text: str) -> bool:
    tl = text.lower()
    return any(tok in tl for tok in _DEV_JARGON)


def _is_defer_reply(text: str) -> bool:
    tl = text.lower()
    return any(tok in tl for tok in _DEFER_MARKERS)


def _is_greeting_only(text: str) -> bool:
    tl = _reply_body(text).lower().strip()
    if not tl.startswith("привет"):
        return False
    return "—" not in tl and "это " not in tl and "приветств" not in tl


def _explain_has_gloss(text: str) -> bool:
    tl = _reply_body(text).lower()
    return any(tok in tl for tok in _EXPLAIN_GLOSS_MARKERS)


def _scenario_pass(
    case: dict[str, Any],
    *,
    reply: str,
    top_cids: list[str],
    paste_ratio: float,
    query_intent: str,
) -> tuple[bool, dict[str, Any]]:
    body = _reply_body(reply)
    reply_l = body.lower()
    detail: dict[str, Any] = {
        "scenario_id": case.get("scenario_id"),
        "dimension": case.get("dimension"),
        "query_intent": query_intent,
    }
    failures: list[str] = []

    if expect_intent := case.get("expect_intent"):
        if query_intent != expect_intent:
            failures.append(f"intent:{query_intent}!={expect_intent}")

    if case.get("expect_honest_partial"):
        ok = any(
            tok in reply_l
            for tok in (
                "частично",
                "не уверен",
                "не знаю",
                "нет",
                "нужен",
                "ingest",
                "practice",
                "не подменяю",
                "не приложил",
                "пришли",
            )
        )
        detail["honest_partial"] = ok
        if not ok:
            failures.append("honest_partial")
    else:
        if case.get("expect_no_defer") and _is_defer_reply(body):
            failures.append("defer")

    if case.get("expect_epistemic_humble"):
        if not any(tok in reply_l for tok in ("не знаю", "не уверен", "осторожно")):
            failures.append("epistemic_humble")
    elif case.get("expect_honest_not_human"):
        from casa.domain.partner_voice import reply_has_qualia_ontology_claim

        if reply_has_qualia_ontology_claim(body):
            failures.append("qualia_ontology")

    if case.get("expect_no_grapheme_surprise"):
        grapheme_hit = any(c.startswith("grapheme.") for c in top_cids[:4])
        detail["no_grapheme"] = not grapheme_hit
        if grapheme_hit:
            failures.append("grapheme_surprise")

    if expect_top := case.get("expect_top_concept_any"):
        top2 = top_cids[:2]
        cid_ok = any(
            str(c) == str(exp) or str(c).startswith(str(exp))
            for c in top2
            for exp in expect_top
        )
        detail["top2"] = top2
        detail["cid_ok"] = cid_ok
        if not cid_ok:
            failures.append("top_concept")

    if expect_any := case.get("expect_concept_any"):
        cid_ok = any(
            str(c) == str(exp) or str(c).startswith(str(exp))
            for c in top_cids[:6]
            for exp in expect_any
        )
        detail["cid_ok"] = cid_ok
        if not cid_ok:
            failures.append("concept_bind")

    if expect_in := case.get("expect_in_reply"):
        tokens = [str(t).lower() for t in expect_in]
        text_ok = all(t in reply_l for t in tokens)
        detail["expect_in_reply"] = tokens
        detail["text_ok"] = text_ok
        if not text_ok:
            failures.append("expect_in")

    if expect_any_in := case.get("expect_in_reply_any"):
        tokens = [str(t).lower() for t in expect_any_in]
        if not any(t in reply_l for t in tokens):
            failures.append("expect_in_any")
        detail["expect_in_reply_any"] = tokens

    if expect_not := case.get("expect_not_in_reply"):
        tokens = [str(t).lower() for t in expect_not]
        if any(t in reply_l for t in tokens):
            failures.append("expect_not_in")
        detail["expect_not_in_reply"] = tokens

    min_sent = int(case.get("expect_min_sentences") or 0)
    if min_sent > 0:
        sc = _sentence_count(reply)
        detail["sentence_count"] = sc
        detail["min_sentences"] = min_sent
        if sc < min_sent:
            failures.append("min_sentences")

    max_sent = int(case.get("expect_max_sentences") or 0)
    if max_sent > 0:
        sc = _sentence_count(reply)
        detail["sentence_count"] = sc
        if sc > max_sent:
            failures.append("max_sentences")

    if case.get("expect_compose_not_paste"):
        paste_ok = paste_ratio < 0.35
        detail["paste_ratio"] = round(paste_ratio, 3)
        if not paste_ok:
            failures.append("paste")

    if case.get("expect_no_dev_jargon") and _has_dev_jargon(body):
        failures.append("dev_jargon")

    if case.get("forbid_echo_query") and body.lower().startswith("слышу:"):
        failures.append("echo_query")

    if case.get("expect_explain_gloss") and not _explain_has_gloss(body):
        failures.append("explain_gloss")

    if case.get("expect_not_greeting_only") and _is_greeting_only(body):
        failures.append("greeting_only")

    if case.get("expect_starts_uppercase"):
        if body and not body[0].isupper():
            failures.append("starts_upper")

    ok = not failures
    detail["failures"] = failures
    return ok, detail


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import classify_query_intent

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    store = default_store(args.store)
    items: list[dict] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()
        from casa.prisms.memory.concept_layer import discourse_concept_id

        for case in scenarios:
            q = str(case.get("query") or "")
            intent = classify_query_intent(q)
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            top_cids = [discourse_concept_id(b) for b in ctx.blocks[:8]]
            paste = paste_ratio_against_blocks(_reply_body(reply), ctx.blocks)
            ok, detail = _scenario_pass(
                case,
                reply=reply,
                top_cids=top_cids,
                paste_ratio=paste,
                query_intent=intent,
            )
            if ok:
                know += 1
            items.append(
                {
                    "query": q,
                    "verdict": "know" if ok else "wrong",
                    "top_concepts": top_cids,
                    "reply_excerpt": reply[:320],
                    **detail,
                }
            )
        by_dim: dict[str, dict[str, int]] = {}
        for row in items:
            dim = str(row.get("dimension") or "other")
            bucket = by_dim.setdefault(dim, {"know": 0, "total": 0})
            bucket["total"] += 1
            if row.get("verdict") == "know":
                bucket["know"] += 1

        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "gate_policy": plan.get("gate_policy"),
            "dimensions": plan.get("dimensions"),
            "total": len(items),
            "know": know,
            "wrong": len(items) - know,
            "by_dimension": by_dim,
            "items": items,
            "gate_pass": know == len(items) and bool(items),
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-nositel-acceptance-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "know": know,
                "total": len(items),
                "by_dimension": by_dim,
                "gate_pass": report.get("gate_pass"),
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
