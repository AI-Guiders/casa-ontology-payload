#!/usr/bin/env python3
"""Write@sketch baseline for phrase-memory literacy stores (no KB bundle grid)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_vc = Path(__file__).resolve().parent
if str(_vc) not in sys.path:
    sys.path.insert(0, str(_vc))
from vc_paths import install  # noqa: E402

install(__file__)

from casa.prisms.visual.phrase_compose import load_phrase_events  # noqa: E402


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE) if len(w) >= 3}


def _event_tokens(entry: dict) -> set[str]:
    out: set[str] = set()
    for w in entry.get("words") or []:
        if isinstance(w, dict) and w.get("surface"):
            out.add(str(w["surface"]).lower())
    for surface in entry.get("surfaces") or []:
        out |= _tokens(str(surface))
    return out


def _pick_event(query: str, entries: list[dict]) -> dict:
    qtok = _tokens(query)
    best: dict | None = None
    best_score = -1
    for entry in entries:
        score = len(qtok & _event_tokens(entry))
        if score > best_score:
            best_score = score
            best = entry
    return best or (entries[0] if entries else {})


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?…]+", text))


def _hit_write(text: str, expect: list[str], *, min_len: int, min_sentences: int) -> bool:
    if len(text.strip()) < min_len:
        return False
    if _sentence_count(text) < min_sentences:
        return False
    blob = text.lower()
    if expect and not any(e.lower() in blob for e in expect):
        return False
    if "понял:" not in blob:
        return False
    return True


def _compose_answer(query: str, entry: dict) -> str:
    surfaces = list(entry.get("surfaces") or [])
    phrase = surfaces[0] if surfaces else ""
    words = [str(w.get("surface") or "") for w in entry.get("words") or [] if isinstance(w, dict)]
    if not phrase and words:
        phrase = " ".join(words)
    agreement = entry.get("agreement") or []
    agr = ""
    if agreement and isinstance(agreement[0], dict):
        a = agreement[0]
        agr = (
            f" Согласование: {a.get('agent', '')} + {a.get('verb', '')}"
            f" ({a.get('kind', 'subjectVerb')})."
        )
    short_q = query.strip()
    if len(short_q) > 90:
        short_q = short_q[:87] + "…"
    body = f"В памяти фраза: «{phrase}».{agr} Слова: {', '.join(words)}."
    return f"Понял: ответ по запросу — «{short_q}». {body}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--min-len", type=int, default=80)
    p.add_argument("--min-sentences", type=int, default=2)
    args = p.parse_args()

    entries = load_phrase_events()
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]
    results = []
    hits = 0
    for row in lines:
        q = row["query"]
        expect_raw = row.get("expect_any") or row.get("expect_substr")
        if isinstance(expect_raw, str):
            expect = [expect_raw]
        elif expect_raw:
            expect = list(expect_raw)
        else:
            expect = []
        t0 = time.perf_counter()
        entry = _pick_event(q, entries)
        text = _compose_answer(q, entry)
        ms = (time.perf_counter() - t0) * 1000
        ok = _hit_write(text, expect, min_len=args.min_len, min_sentences=args.min_sentences)
        hits += 1 if ok else 0
        results.append(
            {
                "query": q,
                "hit": ok,
                "wall_ms": round(ms, 2),
                "event_id": entry.get("event_id"),
                "answer_len": len(text),
                "sentences": _sentence_count(text),
                "preview": text[:200],
            }
        )

    report = {
        "store": str(args.store_dir),
        "bench": "phrase_sketch",
        "queries": len(lines),
        "write_at_sketch": hits / len(lines) if lines else 0.0,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
