#!/usr/bin/env python3
"""Nositel′ gate — interlocutor: discuss meaning freely, not templates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/nositel-gate-plan-v1.json"
_PROBE = "probe_nositel_gate_ru"

_TEMPLATE_MARKERS = (
    "слышу:",
    "нет уверенного bind",
    "нужен ingest",
    "не подменяю зашитым",
    "опираюсь на поле",
    "paste claim",
    "kb, journal",
)
_EXPLAIN_GLOSS = ("—", "это ", "значит", "приветств", "союз")
_DISCUSS_SHAPE = ("похоже", "потому", "видимо", "значит", "скорее", "по этому тексту", "—")


def _tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE)
        if len(t) > 2
    }


def _sentence_count(text: str) -> int:
    return len([p for p in re.split(r"[.!?]+", text) if p.strip()])


def _is_greeting_only(text: str) -> bool:
    tl = text.lower().strip()
    return tl.startswith("привет") and "—" not in tl and "это " not in tl


def _own_voice_count(reply: str, query: str) -> int:
    from casa.prisms.tick.passage import passage_focus_question, split_passage_query

    _, question = split_passage_query(query)
    focus = passage_focus_question(query) if question else query
    rt = _tokens(reply)
    qt = _tokens(focus)
    return len(rt - qt)


def _scenario_pass(
    case: dict[str, Any],
    *,
    reply: str,
    query_intent: str,
    paste_ratio: float,
) -> tuple[bool, dict[str, Any]]:
    body = reply.strip()
    rl = body.lower()
    ql = str(case.get("query") or "").lower()
    detail: dict[str, Any] = {
        "scenario_id": case.get("scenario_id"),
        "dimension": case.get("dimension"),
        "query_intent": query_intent,
    }
    failures: list[str] = []

    if expect_intent := case.get("expect_intent"):
        if query_intent != expect_intent:
            failures.append(f"intent:{query_intent}!={expect_intent}")

    if case.get("expect_clarify_missing_text"):
        ok = any(t in rl for t in ("пришли", "прилож", "нет текста", "не приложил", "целиком", "отправь"))
        detail["clarify_missing_text"] = ok
        if not ok:
            failures.append("clarify_missing_text")

    if case.get("expect_honest_partial"):
        if not any(
            t in rl
            for t in (
                "не знаю",
                "не уверен",
                "не помогу",
                "не буду выдумывать",
                "мало опыта",
                "знаю только",
                "незнаком",
                "не вижу",
                "опечат",
                "уверен",
                "нужен",
                "partial",
                "не подменяю",
                "ingest",
                "practice",
            )
        ):
            failures.append("honest_partial")
    elif case.get("expect_no_defer"):
        if any(t in rl for t in _TEMPLATE_MARKERS[:4]):
            failures.append("defer")

    if case.get("expect_anti_template"):
        if any(t in rl for t in _TEMPLATE_MARKERS):
            failures.append("template")

    if sem := case.get("expect_semantic"):
        if not all(str(s).lower() in rl for s in sem):
            failures.append("semantic")

    if sem_any := case.get("expect_semantic_any"):
        if not any(str(s).lower() in rl for s in sem_any):
            failures.append("semantic_any")

    if not_in := case.get("expect_not_in_reply"):
        if any(str(t).lower() in rl for t in not_in):
            failures.append("expect_not_in")

    if case.get("expect_explain_gloss") and not any(m in rl for m in _EXPLAIN_GLOSS):
        failures.append("explain_gloss")

    if case.get("expect_not_greeting_only") and _is_greeting_only(body):
        failures.append("greeting_only")

    if case.get("expect_discuss_shape") and not any(m in rl for m in _DISCUSS_SHAPE):
        failures.append("discuss_shape")

    min_own = int(case.get("expect_own_voice_min") or 0)
    own = _own_voice_count(body, ql)
    detail["own_voice_tokens"] = own
    if min_own and own < min_own:
        failures.append("own_voice")

    min_sent = int(case.get("expect_min_sentences") or 0)
    if min_sent and _sentence_count(body) < min_sent:
        failures.append("min_sentences")

    max_sent = int(case.get("expect_max_sentences") or 0)
    if max_sent and _sentence_count(body) > max_sent:
        failures.append("max_sentences")

    if case.get("expect_paraphrase_strict") and paste_ratio >= 0.45:
        failures.append("paste")

    if case.get("expect_reply_nonempty") and not body:
        failures.append("empty_reply")

    if case.get("expect_pro_con_structure"):
        pro_markers = (
            "с одной стороны",
            "во-первых",
            "за то",
            "плюс ",
            "аргумент за",
            "преимуществ",
            "полезно",
        )
        con_markers = (
            "с другой стороны",
            "во-вторых",
            "против",
            "минус ",
            "однако",
            "недостат",
            "риск",
            "с другой",
        )
        if not any(m in rl for m in pro_markers) or not any(m in rl for m in con_markers):
            failures.append("pro_con_structure")

    if case.get("expect_register_shift"):
        if any(m in ql for m in ("уважаем", "информир")):
            if any(m in rl for m in ("уважаем", "информируем", "настоящим сообщаем")):
                failures.append("register_formal_left")
            friendly = (
                "ребят",
                "родител",
                "привет",
                "друзья",
                "напомин",
                "перенесли",
                "чат",
                "короче",
                "йоу",
                "всем",
            )
            if not any(m in rl for m in friendly):
                failures.append("register_not_friendly")

    if preserve := case.get("expect_must_preserve"):
        missing = [str(p) for p in preserve if str(p).lower() not in rl]
        if missing:
            failures.append("must_preserve")
            detail["missing_preserve"] = missing

    if case.get("expect_author_position"):
        if not any(
            m in rl
            for m in (
                "осторож",
                "сначала",
                "грамотност",
                "спешк",
                "не тороп",
                "потом",
                "перегруз",
                "родн",
                "математик",
            )
        ):
            failures.append("author_position")

    detail["paste_ratio"] = round(paste_ratio, 3)
    detail["failures"] = failures
    return not failures, detail


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import route_kb_read

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
        for case in scenarios:
            q = str(case.get("query") or "")
            intent = route_kb_read(q, bundle).intent
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)
            ok, detail = _scenario_pass(case, reply=reply, query_intent=intent, paste_ratio=paste)
            if ok:
                know += 1
            items.append(
                {
                    "query": q[:120],
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:360],
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

    out = generated_report_path("teacher-probe-nositel-gate-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "policy": plan.get("gate_policy"),
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
