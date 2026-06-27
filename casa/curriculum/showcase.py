#!/usr/bin/env python3
"""Unified showcase of the conceptual network, for the team — one run, three pillars:

  1. ROUND-TRIP   — phrase → language-independent concept graph → phrase (RU/EN), every form.
  2. QUESTIONS    — state a scene, then ask; answered from the graph (memory + ontology).
  3. VALIDATOR    — meaning-equivalence triage of source↔translation (the product thesis).

Deterministic, cross-lingual, auditable, no hallucination. Run: ``showcase.cmd`` or
``python -m casa.curriculum.showcase``.
"""

from __future__ import annotations


def render_showcase(state: dict, lattice_id: str) -> str:
    from casa.curriculum.demo_ask import render_ask_demo
    from casa.curriculum.demo_check import render_check_demo
    from casa.curriculum.demo_meaning import render_demo

    banner = [
        "█" * 64,
        "  ПОНЯТИЙНАЯ СЕТЬ ФОН НЕЙМАНА — ВИТРИНА",
        "  форма → смысл (граф понятий) → форма · вопросы · валидатор",
        "  детерминированно · кросс-язычно · аудируемо · без галлюцинаций",
        "█" * 64, "",
    ]
    # round-trip and validator are read-only; questions persist situations, so run it last
    parts = [
        "\n\n### 1. ROUND-TRIP — перевод и перефраз через граф смысла\n",
        render_demo(state, lattice_id),
        "\n\n### 2. ВОПРОСЫ — диалоговая петля поверх графа\n",
        render_ask_demo(state, lattice_id),
        "\n\n### 3. ВАЛИДАТОР — эквивалентность смысла (продуктовый тезис)\n",
        render_check_demo(state, lattice_id),
    ]
    return "\n".join(banner) + "".join(parts)


def main(argv: list[str] | None = None) -> int:
    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    state, lattice_id = build_meaning_state()
    print(render_showcase(state, lattice_id))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
