"""Person meta cross-check for phrase agreement (L2 person in phrase flow)."""

from __future__ import annotations

import unicodedata

AGENT_PERSON_BY_SURFACE: dict[str, str] = {
    "я": "lang.meta.grammar.person.1sg",
    "ты": "lang.meta.grammar.person.2sg",
    "он": "lang.meta.grammar.person.3sg.masc",
    "она": "lang.meta.grammar.person.3sg.fem",
    "мы": "lang.meta.grammar.person.1pl",
    "вы": "lang.meta.grammar.person.2pl",
    "они": "lang.meta.grammar.person.3pl",
}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def person_id_for_agent_surface(surface: str) -> str:
    return AGENT_PERSON_BY_SURFACE.get(_nfc(surface).lower(), "")


def check_person_agreement(agent_surface: str, expected_person_id: str) -> bool:
    if not expected_person_id:
        return True
    got = person_id_for_agent_surface(agent_surface)
    if not got:
        return True
    return got == expected_person_id
