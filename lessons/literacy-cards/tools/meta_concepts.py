"""Канон semantic concept_id для метаязыка (sync с design § lang.meta.*)."""

from __future__ import annotations

# (frame_slug, surface на JPEG, concept_id)
MetaCard = tuple[str, str, str]

LETTER_CASE_UPPER = "lang.meta.letterCase.upper"
LETTER_CASE_LOWER = "lang.meta.letterCase.lower"
SIZE_LARGE = "lang.meta.size.large"
SIZE_SMALL = "lang.meta.size.small"
COMPARE_GREATER = "lang.meta.compare.greater"
COMPARE_LESS = "lang.meta.compare.less"
COMPARE_EQUAL = "lang.meta.compare.equal"
MEASURE_LENGTH = "lang.meta.measure.length"
MEASURE_WIDTH = "lang.meta.measure.width"
SPATIAL_LEFT_OF = "lang.meta.spatial.leftOf"
SPATIAL_RIGHT_OF = "lang.meta.spatial.rightOf"
SPATIAL_ABOVE_OF = "lang.meta.spatial.aboveOf"
SPATIAL_BELOW_OF = "lang.meta.spatial.belowOf"
SPATIAL_BETWEEN = "lang.meta.spatial.between"
# Угол и ориентация (S4e–S4f; до sweep-квадрата):
ANGLE = "lang.meta.geom.angle"
ANGLE_RIGHT = "lang.meta.geom.angle.right"
ANGLE_ACUTE = "lang.meta.geom.angle.acute"
ANGLE_OBTUSE = "lang.meta.geom.angle.obtuse"
LINES_PARALLEL = "lang.meta.geom.parallel"
LINES_PERPENDICULAR = "lang.meta.geom.perpendicular"

# Грамматическое лицо (ADR-0030); surface = местоимение на JPEG, id = категория.
GRAMMAR_PERSON_1SG = "lang.meta.grammar.person.1sg"
GRAMMAR_PERSON_2SG = "lang.meta.grammar.person.2sg"
GRAMMAR_PERSON_3SG_MASC = "lang.meta.grammar.person.3sg.masc"
GRAMMAR_PERSON_3SG_FEM = "lang.meta.grammar.person.3sg.fem"
GRAMMAR_PERSON_1PL = "lang.meta.grammar.person.1pl"
GRAMMAR_PERSON_2PL = "lang.meta.grammar.person.2pl"
GRAMMAR_PERSON_3PL = "lang.meta.grammar.person.3pl"

# (frame_slug, surface на JPEG, concept_id)
GRAMMAR_PERSON_CARDS: list[MetaCard] = [
    ("person-1sg", "я", GRAMMAR_PERSON_1SG),
    ("person-2sg", "ты", GRAMMAR_PERSON_2SG),
    ("person-3sg-masc", "он", GRAMMAR_PERSON_3SG_MASC),
    ("person-3sg-fem", "она", GRAMMAR_PERSON_3SG_FEM),
    ("person-1pl", "мы", GRAMMAR_PERSON_1PL),
    ("person-2pl", "вы", GRAMMAR_PERSON_2PL),
    ("person-3pl", "они", GRAMMAR_PERSON_3PL),
]

# План ADR-0030: lang.meta.grammar.number.*, .gender.*, .case.*, .agreement.*

# Синонимы surface (отдельные moment'ы, тот же concept_id):
#   leftOf  — «левее» / «слева»     rightOf — «правее» / «справа»
#   aboveOf — «выше» / «сверху»     belowOf — «ниже» / «снизу»
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
    ("size-large", "большая", SIZE_LARGE),
    ("size-small", "маленькая", SIZE_SMALL),
]

# Регистр (канон); legacy в store — CANONICAL_ALIASES в casa/prisms/memory/meta_concept_aliases.py
REGISTER_CAPITAL = LETTER_CASE_UPPER
REGISTER_LOWERCASE = LETTER_CASE_LOWER

# L2+ грамматика (ADR-0030 / ADR-0033)
GRAMMAR_CASE_NOM = "lang.meta.grammar.case.nom"
GRAMMAR_CASE_ACC = "lang.meta.grammar.case.acc"
GRAMMAR_AGREEMENT_FEM_SG_PAST = "lang.meta.grammar.agreement.subjectVerb.fem.sg.past"
GRAMMAR_AGREEMENT_MASC_SG_PAST = "lang.meta.grammar.agreement.subjectVerb.masc.sg.past"

GRAMMAR_CASE_CARDS: list[MetaCard] = [
    ("case-nom", "именительный падеж", GRAMMAR_CASE_NOM),
    ("case-acc", "винительный падеж", GRAMMAR_CASE_ACC),
]

# Две surface → один agreement id (L3)
GRAMMAR_AGREEMENT_PHRASE_CARDS: list[MetaCard] = [
    ("agr-mama-myla", "мама мыла", GRAMMAR_AGREEMENT_FEM_SG_PAST),
    ("agr-sestra-myla", "сестра мыла", GRAMMAR_AGREEMENT_FEM_SG_PAST),
    ("agr-brat-myl", "брат мыл", GRAMMAR_AGREEMENT_MASC_SG_PAST),
    ("agr-papa-myl", "папа мыл", GRAMMAR_AGREEMENT_MASC_SG_PAST),
]

QUESTION_FRAME_IDS: tuple[str, ...] = (
    "lang.meta.grammar.question.who",
    "lang.meta.grammar.question.what",
    "lang.meta.grammar.question.what_do",
    "lang.meta.grammar.question.which",
    "lang.meta.grammar.question.to_whom",
)
