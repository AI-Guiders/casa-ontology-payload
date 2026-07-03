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


def coverage_report(state: dict, lattice_id: str, pairs: list[tuple[str, str]],
                    langs: tuple[str, str] | None = None) -> dict[str, Any]:
    """How many pairs parse on both sides / one side / neither. ``langs=(src, tgt)``
    declares each side's language when the script can't (en/es are both Latin)."""
    from casa.curriculum.parse import parse_graph

    ls, lt = langs or (None, None)

    def parses(text: str, lang: str | None = None) -> bool:
        return any(e.get("satisfied") for e in parse_graph(state, lattice_id, text, lang=lang).get("edges", []))

    both = src_only = tgt_only = neither = 0
    misses: list[str] = []
    for s, t in pairs:
        ps, pt = parses(s, ls), parses(t, lt)
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


# Spanish relation markers for the ceiling classifier only: a side can (in principle) carry
# a relation if it has a preposition / negation / copula / instruction verb. Kept as a
# separate lang-selected set — Spanish shares the Latin script with English, so mixing the
# sets would misclassify (EN article «a» is an ES preposition, EN «no» is ES negation).
_ES_RELATION_MARKERS = {
    # prepositions
    "en", "de", "con", "sin", "para", "sobre", "a", "por", "durante", "entre", "hasta",
    # negation
    "no", "nunca",
    # copulas / modals
    "es", "está", "están", "son", "debe", "deben", "puede", "pueden",
    # instruction verbs (imperative/usted forms common on labels)
    "use", "utilice", "tome", "tomar", "conserve", "mantenga", "agite", "abra", "cierre",
    "inyecte", "aplique", "deseche", "guarde", "disuelva", "evite", "administre", "contiene",
}


def _side_class(state: dict, lattice_id: str, text: str, lang: str | None = None) -> str:
    """Classify ONE side of a pair for the ceiling. ``parses`` — a satisfied edge was built.
    ``ceiling`` — no word that could carry a relation (a bare label: «Configuration»,
    «Icon Size»); never a validator target, because there is nothing to compare. ``fixable``
    — a relation word IS present but no edge was built (unknown noun / unmodelled structure):
    recoverable in principle by more parser/vocabulary work. ``lang="es"`` selects the
    Spanish marker set (the default RU/EN sets don't know Spanish function words)."""
    from casa.curriculum.parse import _POSITIONAL, _PREPS, _tokens, parse_graph
    from casa.curriculum.situation import PREDICATE_RELATION

    if any(e.get("satisfied") for e in parse_graph(state, lattice_id, text).get("edges", [])):
        return "parses"
    if lang == "es":
        has_relation_word = any(t in _ES_RELATION_MARKERS for t in _tokens(text))
    else:
        has_relation_word = any(
            t in _PREPS or t in _POSITIONAL or (t in PREDICATE_RELATION and t not in _PREPS)
            for t in _tokens(text)
        )
    return "fixable" if has_relation_word else "ceiling"


def ceiling_report(state: dict, lattice_id: str, pairs: list[tuple[str, str]],
                   langs: tuple[str, str] | None = None) -> dict[str, Any]:
    """Pair-level coverage CEILING — the maximum coverage any amount of parser/vocabulary
    work could reach on this corpus. A pair can only ever validate if BOTH sides carry a
    relation; a bare-label side has nothing to compare, so any pair with even one ceiling
    side is structurally out of reach. ``addressable`` (no ceiling side) is that ceiling —
    it separates «grind the parser» from «wrong corpus»: if the ceiling itself is low, the
    text is the problem, not the parser, and the lever is a more controlled domain."""
    from collections import Counter

    combos: Counter = Counter()
    both = 0
    for s, t in pairs:
        cs = _side_class(state, lattice_id, s, lang=langs[0] if langs else None)
        ct = _side_class(state, lattice_id, t, lang=langs[1] if langs else None)
        combos[tuple(sorted((cs, ct)))] += 1
        both += int(cs == "parses" and ct == "parses")
    total = len(pairs) or 1
    addressable = sum(n for combo, n in combos.items() if "ceiling" not in combo)
    return {
        "total": len(pairs),
        "both": both,
        "coverage": round(both / total, 4),
        "addressable": addressable,
        "max_coverage": round(addressable / total, 4),
        "both_ceiling": combos.get(("ceiling", "ceiling"), 0),
        "combos": {f"{a}+{b}": n for (a, b), n in sorted(combos.items(), key=lambda kv: -kv[1])},
    }


def _load_corpus(en_path: str, ru_path: str, limit: int, max_words: int = 8) -> list[tuple[str, str]]:
    with open(en_path, encoding="utf-8") as f:
        en = [ln.strip() for ln in f]
    with open(ru_path, encoding="utf-8") as f:
        ru = [ln.strip() for ln in f]
    pairs = [(e, r) for e, r in zip(en, ru) if e and r and 2 <= len(e.split()) <= max_words]
    return pairs[:limit]


def _load_jsonl(path: str, limit: int, src_key: str = "en", tgt_key: str = "es",
                seed: int | None = None) -> list[tuple[str, str]]:
    """Aligned pairs from a JSONL file (one object per line, e.g. the EMEA candidate pool).

    ``seed=None`` takes the first ``limit`` pairs (fast, order-dependent). A ``seed`` loads
    the WHOLE file and draws a deterministic random sample of ``limit`` — the honest ceiling
    number for the paper is measured this way (order-independent, reproducible)."""
    import json

    if seed is None:
        pairs: list[tuple[str, str]] = []
        with open(path, encoding="utf-8") as f:
            for ln in f:
                if not ln.strip():
                    continue
                row = json.loads(ln)
                s, t = row.get(src_key, ""), row.get(tgt_key, "")
                if s and t:
                    pairs.append((s, t))
                if len(pairs) >= limit:
                    break
        return pairs

    import random

    all_pairs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            row = json.loads(ln)
            s, t = row.get(src_key, ""), row.get(tgt_key, "")
            if s and t:
                all_pairs.append((s, t))
    rng = random.Random(seed)
    rng.shuffle(all_pairs)
    return all_pairs[:limit]


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Validator reality-check (coverage + recall).")
    ap.add_argument("--corpus", nargs=2, metavar=("EN", "RU"), help="aligned bitext (en file, ru file)")
    ap.add_argument("--jsonl", metavar="PATH", help="aligned pairs as JSONL (keys per --langs, e.g. the EMEA pool)")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=None,
                    help="random-sample --limit pairs with this seed (default: first N, order-dependent)")
    ap.add_argument("--max-words", type=int, default=8, help="max source words per pair (bitext filter)")
    ap.add_argument("--langs", nargs=2, metavar=("SRC", "TGT"), default=None,
                    help="side languages for the ceiling classifier (e.g. en es)")
    ap.add_argument("--ceiling", action="store_true",
                    help="report the pair-level coverage ceiling (max reachable by any parser work)")
    args = ap.parse_args(argv)

    state, lat = build_meaning_state()
    if args.jsonl:
        keys = args.langs or ("en", "es")
        pairs = _load_jsonl(args.jsonl, args.limit, src_key=keys[0], tgt_key=keys[1], seed=args.seed)
    elif args.corpus:
        pairs = _load_corpus(args.corpus[0], args.corpus[1], args.limit, max_words=args.max_words)
    else:
        pairs = CURATED_PAIRS

    if args.ceiling:
        cei = ceiling_report(state, lat, pairs, langs=tuple(args.langs) if args.langs else None)
        print("═" * 60)
        print("  ВАЛИДАТОР — ПОТОЛОК ПОКРЫТИЯ (макс. достижимое любым парсером)")
        print("═" * 60)
        print(f"  пар: {cei['total']} · разобраны сейчас: {cei['both']} ({cei['coverage']:.1%})")
        print(f"  ПОТОЛОК (нет «голой» стороны-ярлыка): {cei['addressable']} = {cei['max_coverage']:.1%}")
        print(f"  обе стороны — голый ярлык (структурно недостижимо): {cei['both_ceiling']}")
        print("  раскладка пар (состояния сторон):")
        for combo, n in cei["combos"].items():
            print(f"    {n:5d}  {combo}")
        return 0

    cov = coverage_report(state, lat, pairs, langs=tuple(args.langs) if args.langs else None)
    rec = recall_report(state, lat, RECALL_CASES)
    print("═" * 60)
    print("  ВАЛИДАТОР — ТЕСТ РЕАЛЬНОСТИ")
    print("═" * 60)
    print(f"  ПОКРЫТИЕ ({'корпус' if (args.corpus or args.jsonl) else 'курируемый набор'}): "
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
