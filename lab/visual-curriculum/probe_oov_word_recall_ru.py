#!/usr/bin/env python3
"""ADR-0049 L2: OOV remember → recall on agent journal (smoke v0)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from probe_infra import finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PROBE = "probe_oov_word_recall_v0"
_NOVEL_SURFACE = "криббл"
_NOVEL_CONCEPT = "lang.word.криббл"
_GLOSS = "вымышленное слово: маленький домик у реки"


def _run_smoke(*, store_dir: Path) -> dict:
    setup_probe_imports()
    from casa.domain.subject_dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.memory.agent_memory_ops import agent_recall, agent_remember
    from casa.prisms.memory.memory_prisms import ensure_prisms
    from casa.prisms.shared.store_lock import store_session_lock

    store_dir = store_dir.resolve()
    items: list[dict] = []
    know = 0

    with store_session_lock(store_dir, holder=f"probe:{_PROBE}"):
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        remember_rep = agent_remember(
            store_dir,
            state,
            {
                "kind": "hypothesis",
                "text": f"«{_NOVEL_SURFACE}» — {_GLOSS}.",
                "concepts": [_NOVEL_CONCEPT],
                "tags": ["oov-smoke", "lexicon"],
                "status": "confirmed",
                "test_cues": [_NOVEL_SURFACE, _NOVEL_SURFACE.capitalize()],
            },
            scope="self",
        )
        recall_rep = agent_recall(store_dir, query=_NOVEL_SURFACE, limit=5)
        records = recall_rep.get("records") or []
        recall_hit = any(_NOVEL_SURFACE in str(r.get("text") or "").lower() for r in records)

        wm = WorkingMemory()
        ctx = gather_subject_dialogue_blocks(
            f"Что значит слово «{_NOVEL_SURFACE}»?",
            None,
            state,
            wm,
            store_dir,
            bundle=None,
        )
        bind_hit = any(_NOVEL_CONCEPT in str(b.get("concept_id") or "") for b in ctx.blocks) or any(
            _NOVEL_SURFACE in str(b.get("text") or "").lower() for b in ctx.blocks
        )
        verdict = "know" if remember_rep.get("remembered") and recall_hit and bind_hit else "wrong"
        if verdict == "know":
            know += 1
        items.append(
            {
                "surface": _NOVEL_SURFACE,
                "concept_id": _NOVEL_CONCEPT,
                "verdict": verdict,
                "remembered": remember_rep.get("remembered"),
                "recall_hit": recall_hit,
                "bind_hit": bind_hit,
                "journal_id": remember_rep.get("journal_id"),
            }
        )
        report = {
            "store_id": store_dir.name,
            "probe": _PROBE,
            "total": 1,
            "know": know,
            "wrong": 1 - know,
            "empty": 0,
            "ambiguous": 0,
            "items": items,
        }
        report = finalize_honest_probe_report(state, report, store=store_dir, probe_id=_PROBE)

    return report


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="casa-oov-probe-"))
    try:
        report = _run_smoke(store_dir=tmp)
        path = generated_report_path("teacher-probe-oov-word-recall-v0.json")
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"probe": _PROBE, "know": report.get("know"), "path": str(path)}, ensure_ascii=False))
        raise SystemExit(0 if report.get("know") == 1 else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
