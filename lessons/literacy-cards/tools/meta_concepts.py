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

# Phrase vis: местоимение + глагол (L2 person в phrase flow, как agreement)
GRAMMAR_PERSON_PHRASE_CARDS: list[MetaCard] = [
    ("person-ona-myla", "она мыла", GRAMMAR_PERSON_3SG_FEM),
    ("person-on-myl", "он мыл", GRAMMAR_PERSON_3SG_MASC),
]

# Род и число (ADR-0030) — явные meta id + phrase vis через притяжательное
GRAMMAR_GENDER_MASC = "lang.meta.grammar.gender.masc"
GRAMMAR_GENDER_FEM = "lang.meta.grammar.gender.fem"
GRAMMAR_GENDER_NEUT = "lang.meta.grammar.gender.neut"
GRAMMAR_NUMBER_SG = "lang.meta.grammar.number.sg"
GRAMMAR_NUMBER_PL = "lang.meta.grammar.number.pl"

GRAMMAR_POSSESSIVE_MASC_SG = "lang.meta.grammar.agreement.possessive.masc.sg"
GRAMMAR_POSSESSIVE_FEM_SG = "lang.meta.grammar.agreement.possessive.fem.sg"
GRAMMAR_POSSESSIVE_NEUT_SG = "lang.meta.grammar.agreement.possessive.neut.sg"
GRAMMAR_POSSESSIVE_PL = "lang.meta.grammar.agreement.possessive.pl"

GRAMMAR_GENDER_CARDS: list[MetaCard] = [
    ("gender-masc", "мужской род", GRAMMAR_GENDER_MASC),
    ("gender-fem", "женский род", GRAMMAR_GENDER_FEM),
    ("gender-neut", "средний род", GRAMMAR_GENDER_NEUT),
]

GRAMMAR_NUMBER_CARDS: list[MetaCard] = [
    ("number-sg", "единственное число", GRAMMAR_NUMBER_SG),
    ("number-pl", "множественное число", GRAMMAR_NUMBER_PL),
]

# Он мой / Она моя / Оно моё + head+modifier (моя книга)
GRAMMAR_POSSESSIVE_PHRASE_CARDS: list[MetaCard] = [
    ("poss-rule-sg", "ед.ч.: мой / моя / моё", GRAMMAR_POSSESSIVE_MASC_SG),
    ("poss-rule-pl", "мн.ч.: мои (все роды)", GRAMMAR_POSSESSIVE_PL),
    ("poss-on-moy", "он мой", GRAMMAR_POSSESSIVE_MASC_SG),
    ("poss-ona-moya", "она моя", GRAMMAR_POSSESSIVE_FEM_SG),
    ("poss-ono-moyo", "оно моё", GRAMMAR_POSSESSIVE_NEUT_SG),
    ("poss-oni-moi", "они мои", GRAMMAR_POSSESSIVE_PL),
]

# Синонимы surface (отдельные moment'ы, тот же concept_id):
#   leftOf  — «левее» / «слева»     rightOf — «правее» / «справа»
#   aboveOf — «выше» / «сверху»     belowOf — «ниже» / «снизу»
# Сравнительный размер на vis (один id — разные surface / язык / кадр):
# SIZE_COMPARATIVE_GREATER = "lang.meta.size.comparative.greater"
#   RU: «Этот круг больше других»  EN: «This circle is bigger than the others»
# legacy → канон на read path: casa/prisms/memory/meta_concept_aliases.py

EPISTEMIC_UNKNOWN = "lang.meta.epistemic.unknown"
EPISTEMIC_CHOICE = "lang.meta.epistemic.choice"
EPISTEMIC_CONFUSION = "lang.meta.epistemic.confusion"
LEXICON_GRAPHEME = "lang.meta.lexicon.grapheme"
LEXICON_WORD = "lang.meta.lexicon.word"
GRAMMAR_POS_VERB = "lang.meta.grammar.pos.verb"
GRAMMAR_POS_NOUN = "lang.meta.grammar.pos.noun"
GRAMMAR_POS_ACTION = "lang.meta.grammar.pos.action"

META_LANGUAGE_LETTER_CASE_PHRASE_CARDS: list[MetaCard] = [
    ("capital-zaglavnaya-bukva", "заглавная буква", LETTER_CASE_UPPER),
    ("capital-verhnego-registra", "буква верхнего регистра", LETTER_CASE_UPPER),
    ("lowercase-strochnaya-bukva", "строчная буква", LETTER_CASE_LOWER),
    ("lowercase-nizhnego-registra", "буква нижнего регистра", LETTER_CASE_LOWER),
]

META_LANGUAGE_WAVE1_CARDS: list[MetaCard] = [
    ("bukva", "буква", LEXICON_GRAPHEME),
    ("slovo", "слово", LEXICON_WORD),
    ("zaglavnaya", "заглавная", LETTER_CASE_UPPER),
    ("strochnaya", "строчная", LETTER_CASE_LOWER),
]

META_LANGUAGE_WAVE2_CARDS: list[MetaCard] = [
    ("ne_znayu", "не знаю", EPISTEMIC_UNKNOWN),
    ("vybor", "выбор", EPISTEMIC_CHOICE),
    ("zameshatelstvo", "замешательство", EPISTEMIC_CONFUSION),
    ("glagol", "глагол", GRAMMAR_POS_VERB),
    ("deystvie", "действие", GRAMMAR_POS_ACTION),
    ("sushchestvennoe", "существительное", GRAMMAR_POS_NOUN),
    ("size-large", "большая", SIZE_LARGE),
    ("size-small", "маленькая", SIZE_SMALL),
]

# Back-compat alias
WAVE2_CARDS = META_LANGUAGE_WAVE2_CARDS

# Регистр буквы (графема, блок 1) vs регистр слова/текста (meta.register, блок 7c+)
REGISTER_CAPITAL = LETTER_CASE_UPPER
REGISTER_LOWERCASE = LETTER_CASE_LOWER

# Правила письма на уровне слова/фразы (B2 register — не отдельные lemma)
REGISTER_SENTENCE_INITIAL = "lang.meta.register.sentenceInitial"
REGISTER_ALL_CAPS = "lang.meta.register.allCaps"

REGISTER_META_CARDS: list[MetaCard] = [
    ("register-sentence-initial", "в начале предложения — заглавная", REGISTER_SENTENCE_INITIAL),
    ("register-all-caps-rule", "аббревиатура — все буквы заглавные", REGISTER_ALL_CAPS),
    ("register-apelsin-equals", "апельсин = Апельсин", REGISTER_SENTENCE_INITIAL),
]

REGISTER_WORD_CARDS: list[MetaCard] = [
    ("sssr", "СССР", "lang.word.sssr"),
]

# L2+ грамматика (ADR-0030 / ADR-0033)
GRAMMAR_CASE_NOM = "lang.meta.grammar.case.nom"
GRAMMAR_CASE_ACC = "lang.meta.grammar.case.acc"
GRAMMAR_CASE_DAT = "lang.meta.grammar.case.dat"
GRAMMAR_CASE_GEN = "lang.meta.grammar.case.gen"

GRAMMAR_NUMERAL_CLASS_ONE = "lang.meta.grammar.numeral.class.one"
GRAMMAR_NUMERAL_CLASS_FEW = "lang.meta.grammar.numeral.class.few"
GRAMMAR_NUMERAL_CLASS_MANY = "lang.meta.grammar.numeral.class.many"

GRAMMAR_NUMERAL_CLASS_CARDS: list[MetaCard] = [
    ("numeral-class-one", "1, 21… → им. ед.", GRAMMAR_NUMERAL_CLASS_ONE),
    ("numeral-class-few", "2–4 → им. мн.", GRAMMAR_NUMERAL_CLASS_FEW),
    ("numeral-class-many", "5+, 11–14 → род. мн.", GRAMMAR_NUMERAL_CLASS_MANY),
]

GRAMMAR_NUMERAL_PHRASE_CARDS: list[MetaCard] = [
    ("num-rule-palka", "одна палка … пять палок", GRAMMAR_NUMERAL_CLASS_ONE),
    ("num-one-palka", "одна палка", GRAMMAR_NUMERAL_CLASS_ONE),
    ("num-two-palki", "две палки", GRAMMAR_NUMERAL_CLASS_FEW),
    ("num-five-palok", "пять палок", GRAMMAR_NUMERAL_CLASS_MANY),
]
GRAMMAR_AGREEMENT_FEM_SG_PAST = "lang.meta.grammar.agreement.subjectVerb.fem.sg.past"
GRAMMAR_AGREEMENT_MASC_SG_PAST = "lang.meta.grammar.agreement.subjectVerb.masc.sg.past"

GRAMMAR_CASE_CARDS: list[MetaCard] = [
    ("case-nom", "именительный падеж", GRAMMAR_CASE_NOM),
    ("case-acc", "винительный падеж", GRAMMAR_CASE_ACC),
    ("case-dat", "дательный падеж", GRAMMAR_CASE_DAT),
    ("case-dat-whom", "кому?", GRAMMAR_CASE_DAT),
]

GRAMMAR_QUESTION_CARDS: list[MetaCard] = [
    ("question-who", "кто?", "lang.meta.grammar.question.who"),
    ("question-what", "что?", "lang.meta.grammar.question.what"),
    ("question-what_do", "что делает?", "lang.meta.grammar.question.what_do"),
    ("question-which", "какой?", "lang.meta.grammar.question.which"),
    ("question-to_whom", "кому?", "lang.meta.grammar.question.to_whom"),
    ("question-when", "когда?", "lang.meta.grammar.question.when"),
    ("question-how", "как?", "lang.meta.grammar.question.how"),
    ("question-whose", "чей?", "lang.meta.grammar.question.whose"),
    ("question-whose_pl", "чьи?", "lang.meta.grammar.question.whose_pl"),
    ("question-which_gender", "какого рода?", "lang.meta.grammar.question.which_gender"),
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
    "lang.meta.grammar.question.when",
    "lang.meta.grammar.question.how",
    "lang.meta.grammar.question.whose",
    "lang.meta.grammar.question.whose_pl",
    "lang.meta.grammar.question.which_gender",
)

# Морфемные роли (B5 / morph-role-ru bootstrap)
MORPH_PREFIX = "lang.meta.morph.prefix"
MORPH_ROOT = "lang.meta.morph.root"
MORPH_SUFFIX = "lang.meta.morph.suffix"
MORPH_STEM = "lang.meta.morph.stem"
MORPH_ENDING = "lang.meta.morph.ending"

MORPH_ROLE_CARDS: list[MetaCard] = [
    ("morph-prefix", "приставка", MORPH_PREFIX),
    ("morph-root", "корень", MORPH_ROOT),
    ("morph-suffix", "суффикс", MORPH_SUFFIX),
    ("morph-stem", "основа", MORPH_STEM),
    ("morph-ending", "окончание", MORPH_ENDING),
]

# Attested сегменты (experiential; bind к meta role на поле)
SEGMENT_MYL = "lang.word.myl"
SEGMENT_MYLA = "lang.word.myla"
SEGMENT_PO = "lang.word.po_prefix"
SEGMENT_ENDING_A = "lang.word.ending_a"

MORPH_SEGMENT_CARDS: list[MetaCard] = [
    ("segment-myl", "мыл", SEGMENT_MYL),
    ("segment-myla", "мыла", SEGMENT_MYLA),
    ("segment-po", "по-", SEGMENT_PO),
    ("segment-a", "-а", SEGMENT_ENDING_A),
]

# Agent surface (lower) → person meta id for agreement cross-check
AGENT_PERSON_BY_SURFACE: dict[str, str] = {
    "я": GRAMMAR_PERSON_1SG,
    "ты": GRAMMAR_PERSON_2SG,
    "он": GRAMMAR_PERSON_3SG_MASC,
    "она": GRAMMAR_PERSON_3SG_FEM,
    "мы": GRAMMAR_PERSON_1PL,
    "вы": GRAMMAR_PERSON_2PL,
    "они": GRAMMAR_PERSON_3PL,
}
