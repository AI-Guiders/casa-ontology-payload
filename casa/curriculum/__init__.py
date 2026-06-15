"""Auto-curriculum: structured teaching, verification, translation, orchestration."""

from casa.curriculum.compose import (
    apply_conditioned_rule,
    apply_order_rule,
    apply_suffix_rule,
    compose_en_np,
    gate_conditioned_rule,
    gate_suffix_rule,
    induce_conditioned_rule,
    induce_suffix,
    teach_conditioned_rule,
    teach_order_rule,
    teach_suffix_rule,
)
from casa.curriculum.glossary import load_pairs, teach_glossary
from casa.curriculum.loop import default_generator, mine_targets, run_curriculum
from casa.curriculum.metrics import coverage
from casa.curriculum.sentence import (
    compose_sentence,
    gate_sentence_order,
    induce_order_from_examples,
    teach_sentence_order,
)
from casa.curriculum.staging import stage_and_promote
from casa.curriculum.teach import teach
from casa.curriculum.translate import concepts_for_term, script_of, translate_term

__all__ = [
    "teach",
    "teach_glossary",
    "load_pairs",
    "induce_suffix",
    "teach_suffix_rule",
    "apply_suffix_rule",
    "gate_suffix_rule",
    "induce_conditioned_rule",
    "teach_conditioned_rule",
    "apply_conditioned_rule",
    "gate_conditioned_rule",
    "teach_order_rule",
    "apply_order_rule",
    "compose_en_np",
    "induce_order_from_examples",
    "teach_sentence_order",
    "compose_sentence",
    "gate_sentence_order",
    "stage_and_promote",
    "mine_targets",
    "run_curriculum",
    "default_generator",
    "coverage",
    "translate_term",
    "concepts_for_term",
    "script_of",
]
