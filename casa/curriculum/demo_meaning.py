#!/usr/bin/env python3
"""Curated round-trip demo — one scripted run that shows the conceptual network off.

Each step feeds a phrase through text → language-independent concept graph → text, and
prints the graph plus the RU paraphrase and EN translation. The script is ordered to tell
a story: a sentence normalises to its meaning; different word orders and different
languages collapse to the SAME graph; nesting composes; and a category error is REFUSED
with a reason — proof the system validates meaning, not strings.

Run it: ``demo-meaning.cmd`` or ``python -m casa.curriculum.demo_meaning``.
``DEMO_SCRIPT`` is data so a test can drive the same run headlessly.
"""

from __future__ import annotations

from typing import Any

# (section caption, [phrases]). Phrases in one section share a teaching point.
DEMO_SCRIPT: list[tuple[str, list[str]]] = [
    ("Перефраз через смысл — «лежит» отбрасывается, форма нормализуется",
     ["яблоко лежит на столе"]),
    ("Инвариантность к порядку слов — тот же граф",
     ["на столе яблоко"]),
    ("Перевод через смысл — RU→EN и EN→RU дают один граф",
     ["яблоко на столе", "The apple is on the table"]),
    ("Вложенность — отношения композируются",
     ["яблоко на столе у окна"]),
    ("Прилагательные — модификатор на узле, RU согласуется по роду",
     ["красное яблоко на столе", "red apple on the table"]),
    ("Переходные ситуации — отношение несёт глагол",
     ["студент читает книгу", "большая собака ест мясо"]),
    ("Из чего сделано — отношение made_of, материал в родительном",
     ["стол сделан из древесины", "The cup is made of glass"]),
    ("Софт-домен: действия над объектами интерфейса (декларатив)",
     ["пользователь открывает файл", "The user deletes the folder"]),
    ("Софт-домен: императивы-инструкции (неявное «ты»)",
     ["открой файл", "сохрани документ", "Click the button"]),
    ("Отрицание — полярность входит в смысл (потерянное «не» ≠ та же ситуация)",
     ["не закрывай окно", "Do not delete the file", "яблоко не на столе"]),
    ("Отказ при бессмыслице — валидируется смысл, а не строки",
     ["стол ест яблоко", "камень пьёт воду"]),
]


def render_demo(state: dict, lattice_id: str, script: list[tuple[str, list[str]]] | None = None) -> str:
    """Render the whole scripted demo to a single string (no I/O)."""
    from casa.curriculum.parse import parse_graph
    from casa.curriculum.render import render_round_trip
    from casa.curriculum.roundtrip import realize_graph

    out: list[str] = []
    out.append("═" * 64)
    out.append("  ПОНЯТИЙНАЯ СЕТЬ — перевод и перефраз через граф смысла")
    out.append("  фраза → язык-независимый граф понятий → фраза (RU/EN)")
    out.append("═" * 64)
    for n, (caption, phrases) in enumerate(script if script is not None else DEMO_SCRIPT, 1):
        out.append("")
        out.append(f"[{n}] {caption}")
        for text in phrases:
            graph = parse_graph(state, lattice_id, text)
            if not graph.get("edges"):
                out.append(f"  вход: «{text}»\n  · не разобрал (нет известных понятий/отношений)")
                continue
            ru = realize_graph(state, lattice_id, graph, lang="ru")
            en = realize_graph(state, lattice_id, graph, lang="en")
            out.append(render_round_trip(graph, source=text, ru=ru, en=en))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()  # box-drawing / Cyrillic must not crash a legacy console
    from casa.curriculum.world import build_meaning_state

    state, lattice_id = build_meaning_state()
    print(render_demo(state, lattice_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
