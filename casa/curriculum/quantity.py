#!/usr/bin/env python3
"""Quantities on concept nodes — «два файла», «three red books».

A count is a node modifier (like an adjective): «два файла» is the file node with
count=2. The count enters the situation fingerprint, so «два файла» and «три файла» are
DISTINCT situations — the other half of the validator kernel (numbers + units + negation;
a 5↔50 mistranslation must be id-visible, like a dropped «не»).

Russian numeral agreement is a given lexicon + the case the count governs:
  1            → nominative singular, the numeral agrees in gender («один файл», «одна книга»)
  2,3,4        → genitive singular («два файла», «три книги»)
  5 and up     → genitive plural — out of scope here (no gen-pl rule); the count is still
                 captured in the graph/fingerprint, only the surface is approximated.
English is regular: numeral word + plural noun for count≠1.
"""

from __future__ import annotations

import re

# integer -> (masc/neuter form, feminine form). Gender only differs for 1 and 2.
_RU_CARDINAL: dict[int, tuple[str, str]] = {
    1: ("один", "одна"), 2: ("два", "две"), 3: ("три", "три"), 4: ("четыре", "четыре"),
    5: ("пять", "пять"), 6: ("шесть", "шесть"), 7: ("семь", "семь"), 8: ("восемь", "восемь"),
    9: ("девять", "девять"), 10: ("десять", "десять"),
}
_EN_CARDINAL: dict[int, str] = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}
# every surface (Russian neuter form, feminine form, English word) -> integer
_SURFACE_TO_INT: dict[str, int] = {}
for _n, (_m, _f) in _RU_CARDINAL.items():
    _SURFACE_TO_INT[_m] = _n
    _SURFACE_TO_INT[_f] = _n
for _n, _w in _EN_CARDINAL.items():
    _SURFACE_TO_INT[_w] = _n
# «одно» (neuter of 1) is a real surface too
_SURFACE_TO_INT["одно"] = 1


def number_of_token(token: str) -> int | None:
    """Return the integer for a number surface («два», «two», «3»), or None."""
    t = token.strip().lower()
    if t.isdigit():
        return int(t)
    return _SURFACE_TO_INT.get(t)


def ru_number_word(count: int, gender: str) -> str:
    """The Russian numeral, agreeing in gender for 1 and 2 (gender ∈ {m,n,f})."""
    forms = _RU_CARDINAL.get(count)
    if not forms:
        return str(count)
    return forms[1] if gender == "f" else forms[0]


def en_number_word(count: int) -> str:
    return _EN_CARDINAL.get(count, str(count))


def ru_noun_case(count: int) -> str:
    """Which case the count governs: nominative (1), genitive singular (2-4), gen-pl (5+)."""
    if count == 1:
        return "nom"
    if 2 <= count <= 4:
        return "gen"
    return "gen-pl"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\wЀ-ӿ]+", str(text or "").lower(), flags=re.UNICODE)
