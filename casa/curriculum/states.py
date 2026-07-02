#!/usr/bin/env python3
"""Predicative states — «файл открыт», «кнопка активна», «the window is hidden».

A state is a predicative property of one thing — «the file IS open» — so, like a colour
(«яблоко красное» → color_of), it is a one-place predicate modelled as the relation
``has_state(thing, state)``. The state id is the English word (open/active/hidden) — the
same language-independent convention node labels use, so «файл открыт» and «the file is
open» build the SAME edge. Negation rides the clause polarity: «файл не открыт» is the same
edge with polarity ``neg`` (so it contradicts «файл открыт» — the reasoning kernel).

Russian uses the short-form predicative (открыт/открыта/открыто/открыты), a GIVEN lexicon
by gender (like the adjective/verb lexicons). English is the bare word after the copula
«is/are». Honest scope: a curated software-relevant set in the predicative position; states
are not mutually exclusive here (a file may be open and saved), only polarity contradicts —
open-vs-closed mutual exclusion is future work.
"""

from __future__ import annotations

# state id (English word) -> Russian short-form predicatives by gender (masc/neut/fem/plural)
STATE_LEXICON: dict[str, dict[str, str]] = {
    "open": {"m": "открыт", "n": "открыто", "f": "открыта", "p": "открыты"},
    "closed": {"m": "закрыт", "n": "закрыто", "f": "закрыта", "p": "закрыты"},
    "active": {"m": "активен", "n": "активно", "f": "активна", "p": "активны"},
    "inactive": {"m": "неактивен", "n": "неактивно", "f": "неактивна", "p": "неактивны"},
    "visible": {"m": "виден", "n": "видно", "f": "видна", "p": "видны"},
    "hidden": {"m": "скрыт", "n": "скрыто", "f": "скрыта", "p": "скрыты"},
    "enabled": {"m": "включён", "n": "включено", "f": "включена", "p": "включены"},
    "disabled": {"m": "выключен", "n": "выключено", "f": "выключена", "p": "выключены"},
    "selected": {"m": "выбран", "n": "выбрано", "f": "выбрана", "p": "выбраны"},
    "saved": {"m": "сохранён", "n": "сохранено", "f": "сохранена", "p": "сохранены"},
    "empty": {"m": "пуст", "n": "пусто", "f": "пуста", "p": "пусты"},
    "ready": {"m": "готов", "n": "готово", "f": "готова", "p": "готовы"},
}

STATE_IDS: set[str] = set(STATE_LEXICON)

# Spanish predicative surfaces (participle by gender/number, label style) -> state id.
# None of these collide with EN/RU surfaces, so they merge into the shared lookup;
# «visible» is spelt the same in both languages and maps to the same id anyway.
_ES_STATE_SURFACES: dict[str, str] = {
    "abierto": "open", "abierta": "open", "abiertos": "open", "abiertas": "open",
    "cerrado": "closed", "cerrada": "closed", "cerrados": "closed", "cerradas": "closed",
    "activo": "active", "activa": "active", "activos": "active", "activas": "active",
    "inactivo": "inactive", "inactiva": "inactive", "inactivos": "inactive", "inactivas": "inactive",
    "oculto": "hidden", "oculta": "hidden", "ocultos": "hidden", "ocultas": "hidden",
    "habilitado": "enabled", "habilitada": "enabled",
    "deshabilitado": "disabled", "deshabilitada": "disabled",
    "seleccionado": "selected", "seleccionada": "selected",
    "guardado": "saved", "guardada": "saved",
    "vacío": "empty", "vacía": "empty", "vacio": "empty", "vacia": "empty",
    "listo": "ready", "lista": "ready",
}

# every surface (English word + the Russian short forms + ё/е spelling + Spanish) -> state id
_SURFACE_TO_ID: dict[str, str] = {}
for _sid, _forms in STATE_LEXICON.items():
    _SURFACE_TO_ID[_sid] = _sid
    for _form in _forms.values():
        _SURFACE_TO_ID[_form] = _sid
        if "ё" in _form:  # accept the е spelling too (включен / включён)
            _SURFACE_TO_ID[_form.replace("ё", "е")] = _sid
_SURFACE_TO_ID.update(_ES_STATE_SURFACES)

# EN state words that are ALSO action verbs (collide in PREDICATE_RELATION) — recognised as a
# state only after a copula («the file is open»), never as the imperative «open the file».
AMBIGUOUS_EN = {"open"}

# mutually exclusive states — has_state(x, a) and has_state(x, b) cannot both hold (a thing
# is open OR closed, not both). The reasoning layer reads these as a contradiction, beyond
# the polarity case («open» vs «not open»). Not exhaustive — only clear antonym pairs.
STATE_ANTONYMS: set[frozenset[str]] = {
    frozenset({"open", "closed"}),
    frozenset({"active", "inactive"}),
    frozenset({"visible", "hidden"}),
    frozenset({"enabled", "disabled"}),
}


def are_antonyms(a: str, b: str) -> bool:
    """True if the two state ids are mutually exclusive (open/closed, active/inactive, …)."""
    return frozenset({a, b}) in STATE_ANTONYMS


def state_of_token(token: str) -> str | None:
    """Return the state id for a predicative-state surface (either language), or None."""
    return _SURFACE_TO_ID.get(token.strip().lower())


def ru_state(state_id: str, noun_ru: str) -> str:
    """Russian short-form predicative agreeing with ``noun_ru``'s gender (ending-based)."""
    from casa.curriculum.attributes import _gender_of

    forms = STATE_LEXICON.get(state_id)
    return forms[_gender_of(noun_ru)] if forms else state_id


def en_state(state_id: str) -> str:
    """The English predicative is the state id itself."""
    return state_id
