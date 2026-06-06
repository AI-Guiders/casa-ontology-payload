"""Possessive agreement: правило gender×number → мой/моя/моё/мои (ADR-0033)."""

from __future__ import annotations

import unicodedata
from typing import Any

POSSESSIVE_BY_GENDER_NUMBER: dict[tuple[str, str], str] = {
    ("masc", "sg"): "мой",
    ("fem", "sg"): "моя",
    ("neut", "sg"): "моё",
    ("masc", "pl"): "мои",
    ("fem", "pl"): "мои",
    ("neut", "pl"): "мои",
}

GENDER_ID_TO_KEY: dict[str, str] = {
    "lang.meta.grammar.gender.masc": "masc",
    "lang.meta.grammar.gender.fem": "fem",
    "lang.meta.grammar.gender.neut": "neut",
}

NUMBER_ID_TO_KEY: dict[str, str] = {
    "lang.meta.grammar.number.sg": "sg",
    "lang.meta.grammar.number.pl": "pl",
}

# Местоимение → род (для вывода правила без лексемы в agreement row).
REFERENT_GENDER_ID: dict[str, str] = {
    "он": "lang.meta.grammar.gender.masc",
    "она": "lang.meta.grammar.gender.fem",
    "оно": "lang.meta.grammar.gender.neut",
}

SG_POSSESSIVE_SURFACES = frozenset({"мой", "моя", "моё", "мое"})

POSSESSIVE_RULE_ROWS: tuple[dict[str, str], ...] = (
    {"gender_id": "lang.meta.grammar.gender.masc", "number_id": "lang.meta.grammar.number.sg"},
    {"gender_id": "lang.meta.grammar.gender.fem", "number_id": "lang.meta.grammar.number.sg"},
    {"gender_id": "lang.meta.grammar.gender.neut", "number_id": "lang.meta.grammar.number.sg"},
    {"number_id": "lang.meta.grammar.number.pl"},
)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def expected_possessive_surface(gender_id: str, number_id: str) -> str:
    g = GENDER_ID_TO_KEY.get(gender_id, "")
    n = NUMBER_ID_TO_KEY.get(number_id, "sg")
    if n == "pl":
        return POSSESSIVE_BY_GENDER_NUMBER.get(("masc", "pl"), "мои")
    return POSSESSIVE_BY_GENDER_NUMBER.get((g, n), "")


def is_plural_number(number_id: str) -> bool:
    return NUMBER_ID_TO_KEY.get(number_id, "") == "pl"


def infer_gender_from_referent(surface: str) -> str:
    return REFERENT_GENDER_ID.get(_nfc(surface).lower(), "")


def plural_possessive_trap(got_pos: str, number_id: str) -> str | None:
    if is_plural_number(number_id) and got_pos in SG_POSSESSIVE_SURFACES:
        return "pl_requires_moi_not_sg_possessive"
    return None


def resolve_rule_gender(row: dict[str, Any], got_ref: str) -> str:
    explicit = str(row.get("gender_id") or "").strip()
    if explicit:
        return explicit
    if row.get("infer_gender_from") == "referent" and got_ref:
        return infer_gender_from_referent(got_ref)
    if row.get("infer_gender_from") == "example":
        return ""
    return ""


def resolve_possessive_entry(
    entry: dict[str, Any],
    word_reads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Слить examples[] в плоский entry для probe (иллюстрация ≠ правило)."""
    if not (entry.get("possessive_agreement") or entry.get("possessive_schema")):
        return entry
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
    return out


def agreement_rows_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(entry.get("possessive_agreement") or [])
    if rows:
        return rows
    schema = entry.get("possessive_schema")
    if isinstance(schema, dict) and schema:
        return [schema]
    return []


def check_possessive_agreement(
    slots: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    example_gender_id: str = "",
) -> dict[str, Any]:
    """Gate: притяжательное по правилу gender×number, не по лексеме head/referent."""
    if not rows:
        return {"ok": True, "checked": 0, "details": []}

    details: list[dict[str, Any]] = []
    ok = True
    for row in rows:
        ref_role = str(row.get("head_role") or row.get("referent_role") or "referent")
        if ref_role == "referent" and "head" in slots and "referent" not in slots:
            ref_role = "head"
        if ref_role == "head" and "referent" in slots and "head" not in slots:
            ref_role = "referent"
        pos_role = str(row.get("possessive_role") or "possessive")
        ref_slot = slots.get(ref_role) or slots.get("head") or slots.get("referent") or {}
        pos_slot = slots.get(pos_role) or slots.get("modifier") or {}
        got_ref = _nfc(str(ref_slot.get("surface") or "")).lower()
        got_pos = _nfc(str(pos_slot.get("surface") or "")).lower()

        number_id = str(row.get("number_id") or "lang.meta.grammar.number.sg").strip()
        gender_id = resolve_rule_gender(row, got_ref) or str(example_gender_id or "").strip()

        fail_reason: str | None = None
        row_ok = bool(got_pos)

        trap = plural_possessive_trap(got_pos, number_id) if got_pos else None
        if trap:
            row_ok = False
            fail_reason = trap
        elif not got_pos:
            fail_reason = "missing_possessive"
        elif not is_plural_number(number_id) and not gender_id:
            row_ok = False
            fail_reason = "gender_unresolved"
        else:
            exp_pos = _nfc(
                expected_possessive_surface(
                    gender_id or "lang.meta.grammar.gender.masc",
                    number_id,
                )
            ).lower()
            if got_pos != exp_pos:
                row_ok = False
                fail_reason = "possessive_rule_mismatch"

        if not row_ok:
            ok = False
        details.append(
            {
                "kind": row.get("kind"),
                "gender_id": gender_id or None,
                "number_id": number_id,
                "expected_possessive": expected_possessive_surface(
                    gender_id or "lang.meta.grammar.gender.masc",
                    number_id,
                ),
                "got_referent": got_ref or None,
                "got_possessive": got_pos,
                "fail_reason": fail_reason,
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(rows), "details": details}


def check_possessive_rule_table(
    slots: dict[str, dict[str, Any]],
    *,
    referent_surface: str,
    possessive_surface: str,
    gender_id: str,
    number_id: str,
) -> dict[str, Any]:
    """Synthetic probe: любая иллюстрация, только правило."""
    role = "referent" if infer_gender_from_referent(referent_surface) else "head"
    return check_possessive_agreement(
        {
            role: {"surface": referent_surface},
            "possessive": {"surface": possessive_surface},
        },
        [{"gender_id": gender_id, "number_id": number_id}],
    )
