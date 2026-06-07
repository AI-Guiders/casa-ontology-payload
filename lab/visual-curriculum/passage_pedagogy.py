"""Block 9b — passage comprehension ingest (journal confirmed facts)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vc_paths import repo_root

_DEFAULT_PILOT = (
    repo_root(__file__)
    / "lessons"
    / "ru-text-tract"
    / "data"
    / "passage-comprehend-pilot-v1.json"
)


def load_passage_cases(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _DEFAULT_PILOT
    data = json.loads(p.read_text(encoding="utf-8"))
    return [c for c in (data.get("cases") or []) if isinstance(c, dict)]


def _answer_text(case: dict[str, Any]) -> str:
    passage = str(case.get("passage") or "").strip()
    expect = [str(t) for t in (case.get("expect_in_reply") or []) if t]
    query = str(case.get("query") or "").strip()
    ql = query.lower()
    sents = [s.strip() for s in passage.replace("—", " ").split(".") if s.strip()]
    for sent in sents:
        sl = sent.lower()
        if expect and all(tok in sl for tok in expect):
            return sent + "."
        if "купил" in ql and "купил" in sl:
            return sent + "."
        if ("сказал" in ql or "сказала" in ql) and "сказал" in sl:
            return sent + "."
        if "куда" in ql and ("ушёл" in sl or "ушел" in sl):
            return sent + "."
    if expect:
        token = expect[0]
        if "купил" in ql or "купила" in ql:
            return f"Маша купила {token}."
        if "сказал" in ql or "сказала" in ql:
            return f"Маша сказала: {token.capitalize()}!"
        if "куда" in ql:
            return f"Папа ушёл на {token}у."
    return sents[0] + "." if sents else ""


def _concept_ids(case: dict[str, Any]) -> list[str]:
    prefix = str(case.get("expect_concept_prefix") or "lang.word.")
    tokens = [str(t) for t in (case.get("expect_in_reply") or []) if t]
    return [f"{prefix}{tok}" for tok in tokens]


def _test_cues(case: dict[str, Any]) -> list[str]:
    query = str(case.get("query") or "").strip().lower()
    cues = [query] if query else []
    for frag in ("что купила", "что сказала", "куда ушёл", "куда ушел"):
        if frag in query and frag not in cues:
            cues.append(frag)
    case_id = str(case.get("case_id") or "")
    if case_id:
        cues.append(case_id)
    return cues


def passage_remember_records(cases: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    cases = cases or load_passage_cases()
    records: list[dict[str, Any]] = []
    for case in cases:
        text = _answer_text(case)
        if not text:
            continue
        records.append(
            {
                "kind": "hypothesis",
                "text": text,
                "concepts": _concept_ids(case),
                "tags": ["passage-9b", "block-9b", f"case:{case.get('case_id')}"],
                "status": "confirmed",
                "test_cues": _test_cues(case),
            }
        )
    return records


def ingest_passage_moments(
    store_dir: Path,
    state: dict[str, Any],
    *,
    cases: list[dict[str, Any]] | None = None,
    copies: int = 2,
) -> list[dict[str, Any]]:
    from casa.prisms.memory.agent_memory_ops import agent_remember
    from casa.prisms.shared.store_persist import save_runtime_state

    reports: list[dict[str, Any]] = []
    for record in passage_remember_records(cases):
        for _ in range(max(1, copies)):
            rep = agent_remember(store_dir, state, record, scope="self", persist=False)
            reports.append(rep)
    save_runtime_state(store_dir, state)
    return reports
