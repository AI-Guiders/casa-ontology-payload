#!/usr/bin/env python3
"""Curated reasoning demo — deterministic consistency checking over the concept graph.

The validator (demo_check) asks «does the translation mean the same?». This asks the LOGIC
question «can these statements be true together?» — the same language-independent graph,
generalised from one pair to a SET of claims. One run shows: contradictions on the
dangerous kernel (polarity / quantity / unit) caught cross-lingually, a functional-relation
clash (one colour per thing), entailment by sub-situation containment, cross-lingual
equivalence, honest «unknown» on an unparsed side, and finally a SET-level consistency scan
(«feed N claims → get the contradictions») — the deterministic guardrail LLMs can't promise.

Run: ``reason-demo.cmd`` or ``python -m casa.curriculum.demo_reason``.
"""

from __future__ import annotations

# (caption, A, B) — pairwise relation cases
DEMO_RELATE: list[tuple[str, str, str]] = [
    ("Противоречие: потеряно отрицание (кросс-язычно)", "open the file", "не открывай файл"),
    ("Противоречие: подменено число (2↔3)", "удали два файла", "удали три файла"),
    ("Противоречие: подменена единица (мл↔мг) — доза", "5 мл воды на столе", "5 мг воды на столе"),
    ("Противоречие: один цвет на предмет (функц. отношение)", "яблоко красное", "яблоко синее"),
    ("Следование: вложенный локатив ⊨ голый", "яблоко на столе у окна", "яблоко на столе"),
    ("Эквивалентность: одна ситуация на двух языках", "яблоко на столе", "apple on the table"),
    ("Независимость: разные факты, не спорят", "яблоко на столе", "книга на столе"),
    ("Честность: сторона не разобрана → не судим", "яблоко на столе", "произвольный свободный текст"),
]

# a SET of claims to scan for internal consistency (the headline capability)
DEMO_SET: list[str] = [
    "открой файл",
    "не открывай файл",        # ✗ contradicts «открой файл» (polarity)
    "5 мл воды на столе",
    "5 мг воды на столе",       # ✗ contradicts (unit) — the dangerous dose swap
    "яблоко красное",
    "книга на столе",           # independent of all — fine
]


def render_reason_demo(state: dict, lattice_id: str) -> str:
    from casa.curriculum.reasoning import (
        check_consistency,
        format_consistency,
        format_relation,
        relate,
    )

    out = ["═" * 64,
           "  СЛОЙ РАССУЖДЕНИЯ — детерминированная проверка согласованности",
           "  «могут ли утверждения быть истинны вместе?» · кросс-язычно · аудируемо",
           "═" * 64]
    for n, (caption, a, b) in enumerate(DEMO_RELATE, 1):
        out += ["", f"[{n}] {caption}", format_relation(relate(state, lattice_id, a, b))]
    out += ["", "─" * 64,
            "  Проверка СОГЛАСОВАННОСТИ набора утверждений (подал N → получил противоречия):",
            "─" * 64,
            format_consistency(check_consistency(state, lattice_id, DEMO_SET))]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    state, lattice_id = build_meaning_state()
    print(render_reason_demo(state, lattice_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
