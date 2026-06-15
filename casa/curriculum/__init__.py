"""Auto-curriculum: structured teaching, verification, translation, orchestration."""

from casa.curriculum.glossary import load_pairs, teach_glossary
from casa.curriculum.loop import default_generator, mine_targets, run_curriculum
from casa.curriculum.metrics import coverage
from casa.curriculum.staging import stage_and_promote
from casa.curriculum.teach import teach
from casa.curriculum.translate import concepts_for_term, script_of, translate_term

__all__ = [
    "teach",
    "teach_glossary",
    "load_pairs",
    "stage_and_promote",
    "mine_targets",
    "run_curriculum",
    "default_generator",
    "coverage",
    "translate_term",
    "concepts_for_term",
    "script_of",
]
