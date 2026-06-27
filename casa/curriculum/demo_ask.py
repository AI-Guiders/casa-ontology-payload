#!/usr/bin/env python3
"""Curated dialogue-loop demo — state a scene, then ask the network about it.

Shows the closed loop: a clean clause is understood, validated and REMEMBERED on the field;
a question is then answered from the graph (memory + ontology), not a statistical engine.
Deterministic and auditable. ``ASK_SCRIPT`` is data so a test can drive the same run.
"""

from __future__ import annotations

# statements first (remembered), then questions answered from them
ASK_SCRIPT: list[str] = [
    "красное яблоко на столе",
    "книга на столе",
    "стол сделан из древесины",
    "слон больше собаки",
    "собака больше кошки",
    "— —",  # separator marker (rendered as a divider)
    "что на столе?",
    "из чего стол?",
    "какого цвета яблоко?",
    "съедобно ли яблоко?",
    "можно ли есть стол?",
    "слон больше кошки?",   # transitive inference: never stated directly
]


def render_ask_demo(state: dict, lattice_id: str, script: list[str] | None = None) -> str:
    from casa.curriculum.ask import answer_question, looks_question
    from casa.curriculum.converse import answer_clause, looks_domain

    out = ["═" * 64,
           "  ВОПРОСЫ К СЕТИ — сказал → запомнилось → спросил → ответ из графа",
           "═" * 64, "", "  [говорим ситуации]"]
    for line in script if script is not None else ASK_SCRIPT:
        if line == "— —":
            out.append("\n  [спрашиваем]")
            continue
        if looks_question(line):
            ans = answer_question(state, lattice_id, line)
        elif looks_domain(line):
            ans = answer_clause(state, lattice_id, line)
        else:
            ans = None
        out.append(f"  > {line}")
        out.append(f"    Нейманн: {ans or '(в обычный диалоговый движок)'}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    state, lattice_id = build_meaning_state()
    print(render_ask_demo(state, lattice_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
