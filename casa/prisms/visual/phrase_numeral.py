"""Numeral + noun agreement: class one|few|many (ADR-0033)."""

from __future__ import annotations

import unicodedata
from typing import Any

GENDER_ID_TO_KEY: dict[str, str] = {
    "lang.meta.grammar.gender.masc": "masc",
    "lang.meta.grammar.gender.fem": "fem",
    "lang.meta.grammar.gender.neut": "neut",
}

NUMERAL_CLASS_ONE = "lang.meta.grammar.numeral.class.one"
NUMERAL_CLASS_FEW = "lang.meta.grammar.numeral.class.few"
NUMERAL_CLASS_MANY = "lang.meta.grammar.numeral.class.many"

CASE_NOM = "lang.meta.grammar.case.nom"
CASE_GEN = "lang.meta.grammar.case.gen"
NUMBER_SG = "lang.meta.grammar.number.sg"
NUMBER_PL = "lang.meta.grammar.number.pl"

NUMERAL_SURFACE_TO_VALUE: dict[str, int] = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}

NUMERAL_RULE_ROWS: tuple[dict[str, str], ...] = (
    {"numeral_class_id": NUMERAL_CLASS_ONE, "case_id": CASE_NOM, "number_id": NUMBER_SG},
    {"numeral_class_id": NUMERAL_CLASS_FEW, "case_id": CASE_NOM, "number_id": NUMBER_PL},
    {"numeral_class_id": NUMERAL_CLASS_MANY, "case_id": CASE_GEN, "number_id": NUMBER_PL},
)

DECLENSION_FEM_A_PALATAL = "fem_a_palatal"
PALATAL_STEM_FINALS = frozenset("кгхжчшщ")


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def parse_numeral_value(surface: str) -> int | None:
    return NUMERAL_SURFACE_TO_VALUE.get(_nfc(surface).lower())


def numeral_form_class(n: int) -> str:
    """Russian N + noun: one (1,21…), few (2-4,22-24…), many (0,5-20,11-14,25-30…)."""
    if n < 0:
        return NUMERAL_CLASS_MANY
    mod100 = n % 100
    mod10 = n % 10
    if 11 <= mod100 <= 14:
        return NUMERAL_CLASS_MANY
    if mod10 == 1:
        return NUMERAL_CLASS_ONE
    if 2 <= mod10 <= 4:
        return NUMERAL_CLASS_FEW
    return NUMERAL_CLASS_MANY


def expected_numeral_surface(n: int, gender_id: str) -> str:
    g = GENDER_ID_TO_KEY.get(gender_id, "masc")
    if n == 1:
        return {"masc": "один", "fem": "одна", "neut": "одно"}.get(g, "один")
    if n == 2:
        return "две" if g == "fem" else "два"
    words = {
        3: "три",
        4: "четыре",
        5: "пять",
        6: "шесть",
        7: "семь",
        8: "восемь",
        9: "девять",
        10: "десять",
    }
    return words.get(n, str(n))


def expected_head_grammeme(form_class_id: str) -> tuple[str, str]:
    for row in NUMERAL_RULE_ROWS:
        if row["numeral_class_id"] == form_class_id:
            return row["case_id"], row["number_id"]
    return CASE_NOM, NUMBER_SG


def _fem_a_palatal_paradigm(lemma: str) -> dict[str, str]:
    """-ка на шипящих/звонких: палка → палки / палок (правило, не лексема)."""
    lem = _nfc(lemma)
    if lem.endswith("ка") and len(lem) > 2:
        base = lem[:-2]
        return {"nom_sg": lem, "nom_pl": f"{base}ки", "gen_pl": f"{base}ок"}
    if lem.endswith("а"):
        stem = lem[:-1]
        nom_pl = f"{stem}и" if stem[-1:] in PALATAL_STEM_FINALS else f"{stem}ы"
        gen_pl = f"{stem}" if stem[-1:] in PALATAL_STEM_FINALS else f"{stem}"
        return {"nom_sg": lem, "nom_pl": nom_pl, "gen_pl": gen_pl}
    return {"nom_sg": lem, "nom_pl": lem, "gen_pl": lem}


def expected_head_surface(lemma: str, form_class_id: str, *, declension_id: str) -> str:
    if declension_id == DECLENSION_FEM_A_PALATAL:
        paradigm = _fem_a_palatal_paradigm(lemma)
    else:
        paradigm = _fem_a_palatal_paradigm(lemma)
    if form_class_id == NUMERAL_CLASS_ONE:
        return paradigm["nom_sg"]
    if form_class_id == NUMERAL_CLASS_FEW:
        return paradigm["nom_pl"]
    return paradigm["gen_pl"]


def head_matches_grammeme(
    got_head: str,
    *,
    lemma: str,
    form_class_id: str,
    declension_id: str,
) -> bool:
    exp = _nfc(expected_head_surface(lemma, form_class_id, declension_id=declension_id)).lower()
    return _nfc(got_head).lower() == exp


def resolve_numeral_entry(
    entry: dict[str, Any],
    word_reads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    examples = entry.get("examples")
    if not isinstance(examples, list) or not examples:
        return entry

    if word_reads:
        read_surfs = {_nfc(str(r.get("surface") or "")).lower() for r in word_reads}
        for ex in examples:
            if not isinstance(ex, dict):
                continue
            ex_words = ex.get("words") or []
            ex_surfs = {_nfc(str(w.get("surface") or "")).lower() for w in ex_words if w.get("surface")}
            if ex_surfs and ex_surfs <= read_surfs:
                return _merge_example(entry, ex)

    first = examples[0] if isinstance(examples[0], dict) else {}
    return _merge_example(entry, first)


def _merge_example(entry: dict[str, Any], example: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    for key in ("surfaces", "words", "question_frames"):
        if example.get(key) is not None:
            out[key] = example[key]
    if example.get("gender_id"):
        out["example_gender_id"] = example["gender_id"]
    if example.get("lemma"):
        out["example_lemma"] = example["lemma"]
    return out


def agreement_rows_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(entry.get("numeral_agreement") or [])
    if rows:
        return rows
    schema = entry.get("numeral_schema")
    if isinstance(schema, dict) and schema:
        return [schema]
    return []


def check_numeral_agreement(
    slots: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    example_gender_id: str = "",
    example_lemma: str = "",
) -> dict[str, Any]:
    if not rows:
        return {"ok": True, "checked": 0, "details": []}

    details: list[dict[str, Any]] = []
    ok = True
    for row in rows:
        head_role = str(row.get("head_role") or "head")
        num_role = str(row.get("numeral_role") or "numeral")
        head_slot = slots.get(head_role) or {}
        num_slot = slots.get(num_role) or {}
        got_head = _nfc(str(head_slot.get("surface") or "")).lower()
        got_num = _nfc(str(num_slot.get("surface") or "")).lower()

        gender_id = str(row.get("gender_id") or example_gender_id or "").strip()
        declension_id = str(row.get("declension_id") or DECLENSION_FEM_A_PALATAL).strip()
        lemma = _nfc(str(row.get("lemma") or example_lemma or got_head))

        fail_reason: str | None = None
        row_ok = bool(got_num and got_head)

        value = parse_numeral_value(got_num) if got_num else None
        if not got_num or not got_head:
            fail_reason = "missing_slot"
            row_ok = False
        elif value is None:
            fail_reason = "numeral_unparsed"
            row_ok = False
        elif not gender_id:
            fail_reason = "gender_unresolved"
            row_ok = False
        else:
            form_class = numeral_form_class(value)
            exp_num = _nfc(expected_numeral_surface(value, gender_id)).lower()
            if got_num != exp_num:
                row_ok = False
                fail_reason = "numeral_surface_mismatch"
            elif not head_matches_grammeme(
                got_head,
                lemma=lemma,
                form_class_id=form_class,
                declension_id=declension_id,
            ):
                row_ok = False
                fail_reason = "head_form_mismatch"

        if not row_ok:
            ok = False
        case_id, number_id = (
            expected_head_grammeme(numeral_form_class(value)) if value is not None else ("", "")
        )
        details.append(
            {
                "kind": row.get("kind"),
                "value": value,
                "numeral_class_id": numeral_form_class(value) if value is not None else None,
                "gender_id": gender_id or None,
                "expected_numeral": expected_numeral_surface(value, gender_id) if value else None,
                "expected_head": (
                    expected_head_surface(lemma, numeral_form_class(value), declension_id=declension_id)
                    if value is not None and lemma
                    else None
                ),
                "expected_head_case_id": case_id or None,
                "expected_head_number_id": number_id or None,
                "got_numeral": got_num or None,
                "got_head": got_head or None,
                "fail_reason": fail_reason,
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(rows), "details": details}
