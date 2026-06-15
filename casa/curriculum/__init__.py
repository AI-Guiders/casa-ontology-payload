"""Auto-curriculum: structured teaching + verification + term translation."""

from casa.curriculum.teach import teach
from casa.curriculum.translate import concepts_for_term, script_of, translate_term

__all__ = ["teach", "translate_term", "concepts_for_term", "script_of"]
