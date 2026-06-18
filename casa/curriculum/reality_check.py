#!/usr/bin/env python3
"""Reality-check harness for the validator — measure the two numbers that decide the product.

  COVERAGE — on real source↔translation pairs, on what fraction do we build a meaning graph
             on BOTH sides? (Everything else is honestly «uncheckable».) This is the
             stage-1 wall, as a number: it says how much parser/ontology work remains.
  RECALL   — on the pairs we CAN parse, do we catch the dangerous structured errors
             (dropped «не», swapped number, swapped unit)? This is the whole value prop.

Two honest, independent measurements — a low coverage with a high recall is the expected
shape and the exact story of the thesis: precise on the parseable subset, silent (not
wrong) elsewhere. Run on the built-in curated pairs, or point `--corpus` at an aligned
bitext (two files, one sentence per line): ``python -m casa.curriculum.reality_check
--corpus .scratch/opus/KDE4.en-ru.en .scratch/opus/KDE4.en-ru.ru --limit 2000``.
"""

from __future__ import annotations

from typing import Any

# correct UI-instruction translations in the supported clause forms (for coverage)
CURATED_PAIRS: list[tuple[str, str]] = [
    ("открой файл", "open the file"),
    ("сохрани документ", "save the document"),
    ("удали папку", "delete the folder"),
    ("закрой окно", "close the window"),
    ("нажми кнопку", "click the button"),
    ("не закрывай окно", "do not close the window"),
    ("не удаляй файл", "do not delete the file"),
    ("яблоко на столе", "the apple is on the table"),
    ("книга на столе", "the book is on the table"),
    ("стол сделан из древесины", "the table is made of wood"),
]

# explicit (correct, corrupted, expected-class) triples — the dangerous-error recall set
RECALL_CASES: list[tuple[str, str, str]] = [
    ("не удаляй файл", "удали файл", "polarity"),
    ("не закрывай окно", "закрой окно", "polarity"),
    ("удали два файла", "удали три файла", "quantity"),
    ("две книги на столе", "одна книга на столе", "quantity"),
    ("5 мл воды на столе", "5 мг воды на столе", "unit"),
    ("10 мл воды на столе", "50 мл воды на столе", "quantity"),
]


def coverage_report(state: dict, lattice_id: str, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """How many pairs parse on both sides / one side / neither."""
    from casa.curriculum.parse import parse_graph

    def parses(text: str) -> bool:
        return any(e.get("satisfied") for e in parse_graph(state, lattice_id, text).get("edges", []))

    both = src_only = tgt_only = neither = 0
    misses: list[str] = []
    for s, t in pairs:
        ps, pt = parses(s), parses(t)
        if ps and pt:
            both += 1
        elif ps:
            src_only += 1
            misses.append(t)
        elif pt:
            tgt_only += 1
            misses.append(s)
        else:
            neither += 1
    total = len(pairs) or 1
    return {"total": len(pairs), "both": both, "src_only": src_only, "tgt_only": tgt_only,
            "neither": neither, "coverage": round(both / total, 4), "miss_examples": misses[:8]}


def recall_report(state: dict, lattice_id: str, cases: list[tuple[str, str, str]]) -> dict[str, Any]:
    """On correct→corrupted pairs, is the corruption flagged with the right class?"""
    from casa.curriculum.equivalence import check_equivalence

    tested = caught = 0
    per_class: dict[str, list[int]] = {}
    misses: list[str] = []
    for correct, corrupted, klass in cases:
        r = check_equivalence(state, lattice_id, correct, corrupted)
        if r["verdict"] == "uncheckable":
            continue  # can't even parse — not a recall miss, a coverage gap
        tested += 1
        hit = r["verdict"] == "divergent" and any(d["class"] == klass for d in r["divergences"])
        caught += int(hit)
        per_class.setdefault(klass, [0, 0])
        per_class[klass][0] += int(hit)
        per_class[klass][1] += 1
        if not hit:
            misses.append(f"{correct!r} vs {corrupted!r} (expected {klass})")
    return {"tested": tested, "caught": caught,
            "recall": round(caught / (tested or 1), 4),
            "per_class": {k: f"{a}/{b}" for k, (a, b) in per_class.items()}, "misses": misses}


def _load_corpus(en_path: str, ru_path: str, limit: int) -> list[tuple[str, str]]:
    with open(en_path, encoding="utf-8") as f:
        en = [ln.strip() for ln in f]
    with open(ru_path, encoding="utf-8") as f:
        ru = [ln.strip() for ln in f]
    pairs = [(e, r) for e, r in zip(en, ru) if e and r and 2 <= len(e.split()) <= 8]
    return pairs[:limit]


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Validator reality-check (coverage + recall).")
    ap.add_argument("--corpus", nargs=2, metavar=("EN", "RU"), help="aligned bitext (en file, ru file)")
    ap.add_argument("--limit", type=int, default=2000)
    args = ap.parse_args(argv)

    state, lat = build_meaning_state()
    pairs = _load_corpus(args.corpus[0], args.corpus[1], args.limit) if args.corpus else CURATED_PAIRS
    cov = coverage_report(state, lat, pairs)
    rec = recall_report(state, lat, RECALL_CASES)
    print("═" * 60)
    print("  ВАЛИДАТОР — ТЕСТ РЕАЛЬНОСТИ")
    print("═" * 60)
    print(f"  ПОКРЫТИЕ ({'корпус' if args.corpus else 'курируемый набор'}): "
          f"{cov['both']}/{cov['total']} пар разобраны с обеих сторон = {cov['coverage']:.1%}")
    print(f"    одна сторона: {cov['src_only'] + cov['tgt_only']} · ни одной: {cov['neither']}")
    if cov["miss_examples"]:
        print("    примеры непокрытого:")
        for m in cov["miss_examples"]:
            print(f"      · «{m}»")
    print(f"  RECALL на опасных классах: {rec['caught']}/{rec['tested']} = {rec['recall']:.0%}  {rec['per_class']}")
    if rec["misses"]:
        print(f"    пропуски: {rec['misses']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
