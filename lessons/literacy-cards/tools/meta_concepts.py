"""Канон semantic concept_id для метаязыка (sync с design § lang.meta.*)."""

from __future__ import annotations

# (frame_slug, surface на JPEG, concept_id)
MetaCard = tuple[str, str, str]

LETTER_CASE_UPPER = "lang.meta.letterCase.upper"
LETTER_CASE_LOWER = "lang.meta.letterCase.lower"
# Сравнительный размер на vis (один id — разные surface / язык / кадр):
# SIZE_COMPARATIVE_GREATER = "lang.meta.size.comparative.greater"
#   RU: «Этот круг больше других»  EN: «This circle is bigger than the others»
# legacy → канон на read path: casa/prisms/memory/meta_concept_aliases.py

# Волна 2: concept_id явный; legacy lang.word.* — миграция на lang.meta.* по мере pure-ingest
WAVE2_CARDS: list[MetaCard] = [
    ("ne_znayu", "не знаю", "lang.word.ne_znayu"),
    ("vybor", "выбор", "lang.word.vybor"),
    ("zameshatelstvo", "замешательство", "lang.word.zameshatelstvo"),
    ("glagol", "глагол", "lang.word.glagol"),
    ("deystvie", "действие", "lang.word.deystvie"),
    ("sushchestvennoe", "существительное", "lang.word.sushchestvennoe"),
    ("size-large", "большая", "lang.meta.size.large"),
    ("size-small", "маленькая", "lang.meta.size.small"),
]

# Регистр (канон); legacy в store — CANONICAL_ALIASES в casa/prisms/memory/meta_concept_aliases.py
REGISTER_CAPITAL = LETTER_CASE_UPPER
REGISTER_LOWERCASE = LETTER_CASE_LOWER
