"""Russian morphology via the SAME conditioned inductor (Cyrillic vowel primitive).

Masculine nominative plural is the classic ы/и spelling rule: -и after the velar/
hushing consonants {к г х ж ш ч щ}, else -ы. Because the conditioning consonant is the
masculine stem's last letter, the inductor learns it as a closed class and generalises
to never-taught nouns. Neuter: -о -> -а, -е -> -я. Gate verifies held-out + controls.
"""

from __future__ import annotations

import json

from casa.curriculum import (
    apply_conditioned_rule,
    gate_conditioned_rule,
    induce_conditioned_rule,
    teach_conditioned_rule,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
RULES = REPO_ROOT / "lab/curriculum/ru-rules-v1.json"
LAT = "schema-math"


def _state() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    return state


def _pairs(rule_id: str) -> list[tuple[str, str]]:
    return [tuple(p) for p in json.loads(RULES.read_text(encoding="utf-8"))["rules"][rule_id]]


def test_masc_plural_induces_velar_class() -> None:
    clauses = induce_conditioned_rule(_pairs("lang.rule.plural-nom-m.ru"))
    assert clauses is not None
    # the ы/и spelling rule is induced as the single velar/hushing class K (one clause),
    # not seven memorised consonant literals — so it generalises to any such stem
    assert ("K", 0, "и", False) in clauses
    assert clauses[-1] == ("", 0, "ы", False)       # -ы is the masculine default


def test_masc_plural_gate_and_generalisation() -> None:
    state = _state()
    pairs = _pairs("lang.rule.plural-nom-m.ru")
    rep = gate_conditioned_rule(state, LAT, "lang.rule.plural-nom-m.ru", pairs)
    assert rep["passed"] is True
    assert rep["held_out_pass_rate"] >= 0.9
    assert rep["negative_control_passed"] and rep["ablation_breaks_production"]
    teach_conditioned_rule(state, LAT, "lang.rule.plural-nom-m.ru", pairs)
    a = lambda w: apply_conditioned_rule(state, LAT, "lang.rule.plural-nom-m.ru", w)
    assert a("сапог") == "сапоги" and a("утюг") == "утюги"      # velar -> -и
    assert a("матч") == "матчи" and a("плащ") == "плащи"        # hushing -> -и
    assert a("шкаф") == "шкафы" and a("компьютер") == "компьютеры"  # default -> -ы


def test_neuter_plural_gate_and_generalisation() -> None:
    state = _state()
    pairs = _pairs("lang.rule.plural-nom-n.ru")
    rep = gate_conditioned_rule(state, LAT, "lang.rule.plural-nom-n.ru", pairs)
    assert rep["passed"] is True
    teach_conditioned_rule(state, LAT, "lang.rule.plural-nom-n.ru", pairs)
    a = lambda w: apply_conditioned_rule(state, LAT, "lang.rule.plural-nom-n.ru", w)
    assert a("вино") == "вина" and a("дерево") == "дерева"   # -о -> -а
    assert a("море") == "моря" and a("поле") == "поля"       # -е -> -я


def test_feminine_plural_velar_class_generalises() -> None:
    # the feminine ы/и rule turns on the consonant BEFORE -а — learnable only with the
    # velar/hushing primitive (книга->книги but рыба->рыбы), and it then generalises to
    # never-taught stems including hushing consonants (задача->задачи, свеча->свечи)
    state = _state()
    pairs = _pairs("lang.rule.plural-nom-f.ru")
    clauses = induce_conditioned_rule(pairs)
    assert any(cut == 1 and add == "и" and "K" in cond for cond, cut, add, _ in clauses)
    rep = gate_conditioned_rule(state, LAT, "lang.rule.plural-nom-f.ru", pairs)
    assert rep["passed"] is True and rep["held_out_pass_rate"] >= 0.9
    teach_conditioned_rule(state, LAT, "lang.rule.plural-nom-f.ru", pairs)
    a = lambda w: apply_conditioned_rule(state, LAT, "lang.rule.plural-nom-f.ru", w)
    assert a("эпоха") == "эпохи" and a("задача") == "задачи" and a("свеча") == "свечи"  # velar/hushing -> -и
    assert a("ягода") == "ягоды" and a("берёза") == "берёзы"  # else -> -ы
