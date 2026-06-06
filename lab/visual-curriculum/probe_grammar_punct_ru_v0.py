#!/usr/bin/env python3
"""ADR-0049 L3/L4: grammar + punct KB bind probes (text tract)."""

from __future__ import annotations

import json
from pathlib import Path

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports


_CASES = (
    {
        "query": "Согласно приказа верно?",
        "expect_cid_prefix": "ru.grammar.case.dative",
        "expect_in_reply": ("приказу", "датель"),
    },
    {
        "query": "Нужна ли запятая в «я знаю что он придёт»?",
        "expect_cid_prefix": "ru.grammar.punct",
        "expect_in_reply": ("запят", "что"),
    },
)


def _run_text_kb_probe(*, probe_id: str, cases: tuple[dict, ...], report_filename: str) -> dict:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.subject_dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    store = default_store("von-neumann")
    items: list[dict] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{probe_id}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in cases:
            q = str(case["query"])
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx).lower()
            top_cids = [str(b.get("concept_id") or "") for b in ctx.blocks[:4]]
            prefix = str(case["expect_cid_prefix"])
            cid_ok = any(c.startswith(prefix) for c in top_cids if c)
            text_ok = all(tok in reply for tok in case["expect_in_reply"])
            verdict = "know" if cid_ok and text_ok else "wrong"
            if verdict == "know":
                know += 1
            items.append(
                {
                    "query": q,
                    "verdict": verdict,
                    "top_concepts": top_cids,
                    "reply_excerpt": reply[:160],
                    "cid_ok": cid_ok,
                    "text_ok": text_ok,
                }
            )

        report = {
            "store_id": store.name,
            "probe": probe_id,
            "total": len(items),
            "know": know,
            "wrong": len(items) - know,
            "empty": 0,
            "ambiguous": 0,
            "items": items,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=probe_id)

    path = generated_report_path(report_filename)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": probe_id, "know": know, "total": len(items), "path": str(path)}, ensure_ascii=False))
    return report


def main_ortho() -> None:
    _run_text_kb_probe(
        probe_id="probe_orthography_ru_v0",
        cases=(_CASES[0],),
        report_filename="teacher-probe-orthography-ru-v0.json",
    )


def main_punct() -> None:
    _run_text_kb_probe(
        probe_id="probe_grammar_punct_ru_v0",
        cases=(_CASES[1],),
        report_filename="teacher-probe-grammar-punct-ru-v0.json",
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "punct":
        main_punct()
    else:
        main_ortho()
