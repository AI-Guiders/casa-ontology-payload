#!/usr/bin/env python3
"""Curated validator demo — the meaning-equivalence triage on realistic pairs.

Shows the product thesis in one run: a deterministic, cross-lingual, auditable check that
(1) passes correct translations (incl. correctly-negated ones), (2) CATCHES the dangerous
structured errors — a dropped «не», a swapped number — with a classified, provable note,
and (3) honestly says «uncheckable» when it cannot parse a side, never faking a verdict.

Run: ``check-demo.cmd`` or ``python -m casa.curriculum.demo_check``.
"""

from __future__ import annotations

from typing import Any

# (section caption, source, target)
DEMO_CHECK: list[tuple[str, str, str]] = [
    ("Корректный перевод (кросс-язычно) — проходит", "открой файл", "open the file"),
    ("Корректный перевод локатива", "яблоко на столе", "The apple is on the table"),
    ("Корректное отрицание — НЕ ложное срабатывание", "не закрывай окно", "do not close the window"),
    ("ОПАСНО: потеряно отрицание — поймано детерминированно", "не удаляй файл", "delete the file"),
    ("ОПАСНО: подменено число (2↔3)", "удали два файла", "удали три файла"),
    ("ОПАСНО: число в ситуации", "две книги на столе", "три книги на столе"),
    ("Честность: сторона не разобрана → не проверяем", "открой файл", "произвольный свободный текст"),
]


def render_check_demo(state: dict, lattice_id: str, script: list[tuple[str, str, str]] | None = None) -> str:
    from casa.curriculum.equivalence import check_equivalence, format_check

    out = ["═" * 64,
           "  ВАЛИДАТОР ЭКВИВАЛЕНТНОСТИ — смысл перевода через граф понятий",
           "  детерминированно · кросс-язычно · аудируемо · без галлюцинаций",
           "═" * 64]
    for n, (caption, source, target) in enumerate(script if script is not None else DEMO_CHECK, 1):
        out.append("")
        out.append(f"[{n}] {caption}")
        out.append(format_check(check_equivalence(state, lattice_id, source, target)))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    state, lattice_id = build_meaning_state()
    print(render_check_demo(state, lattice_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
