#!/usr/bin/env python3
"""Adjective attributes on concept nodes — «красное яблоко» carries a modifier.

An adjective is not a binary relation between two concepts, so it is not a graph edge; it
is an ATTRIBUTE on a node. The attribute id is the English adjective word (red/big) — the
same language-independent convention the node labels use, so the graph stays identical
whether the phrase came in Russian or English.

Russian agreement is a GIVEN lexicon of gender forms (like the irregular verbs): the
adjective agrees with the noun's gender, inferred from the noun's ending (consonant→masc,
-о/-е→neuter, -а/-я→feminine). English needs no agreement — the attribute id is the word.

Honest scope: a small curated set in the nominative. Oblique adjective forms («на красном
столе») are out of scope; the parser recognises nominative modifiers, which is what the
controlled demo clauses use.
"""

from __future__ import annotations

# attribute id (English word) -> Russian forms by gender (masc / neuter / fem)
ADJ_LEXICON: dict[str, dict[str, str]] = {
    "red": {"m": "красный", "n": "красное", "f": "красная"},
    "white": {"m": "белый", "n": "белое", "f": "белая"},
    "black": {"m": "чёрный", "n": "чёрное", "f": "чёрная"},
    "green": {"m": "зелёный", "n": "зелёное", "f": "зелёная"},
    "blue": {"m": "синий", "n": "синее", "f": "синяя"},
    "yellow": {"m": "жёлтый", "n": "жёлтое", "f": "жёлтая"},
    "grey": {"m": "серый", "n": "серое", "f": "серая"},
    "brown": {"m": "коричневый", "n": "коричневое", "f": "коричневая"},
    "big": {"m": "большой", "n": "большое", "f": "большая"},
    "small": {"m": "маленький", "n": "маленькое", "f": "маленькая"},
    "hot": {"m": "горячий", "n": "горячее", "f": "горячая"},
    "cold": {"m": "холодный", "n": "холодное", "f": "холодная"},
    "new": {"m": "новый", "n": "новое", "f": "новая"},
    "old": {"m": "старый", "n": "старое", "f": "старая"},
    "clean": {"m": "чистый", "n": "чистое", "f": "чистая"},
    "dirty": {"m": "грязный", "n": "грязное", "f": "грязная"},
    "wet": {"m": "мокрый", "n": "мокрое", "f": "мокрая"},
    "dry": {"m": "сухой", "n": "сухое", "f": "сухая"},
}

# which attribute ids are colours (vs sizes/qualities) — used by the color_of relation/question
COLOR_IDS = {"red", "white", "black", "green", "blue", "yellow", "grey", "brown"}

# every surface (English word + the three Russian nominative forms) -> attribute id
_SURFACE_TO_ID: dict[str, str] = {}
for _aid, _forms in ADJ_LEXICON.items():
    _SURFACE_TO_ID[_aid] = _aid
    for _form in _forms.values():
        _SURFACE_TO_ID[_form] = _aid


def attr_of_token(token: str) -> str | None:
    """Return the attribute id for an adjective surface (either language), or None."""
    return _SURFACE_TO_ID.get(token.strip().lower())


def _gender_of(noun_ru: str) -> str:
    """Russian gender from the noun's ending: -о/-е neuter, -а/-я feminine, else masc."""
    end = noun_ru[-1:].lower()
    if end in "ое":
        return "n"
    if end in "ая":
        return "f"
    return "m"


def ru_adjective(attr_id: str, noun_ru: str) -> str:
    """The Russian adjective form that agrees with ``noun_ru``'s gender."""
    forms = ADJ_LEXICON.get(attr_id)
    if not forms:
        return attr_id
    return forms[_gender_of(noun_ru)]


def en_adjective(attr_id: str) -> str:
    """The English adjective is the attribute id itself."""
    return attr_id
