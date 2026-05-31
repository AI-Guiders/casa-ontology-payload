#!/usr/bin/env python3
"""Internal reconcile after failed verify — no teacher, no gold."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.sss_segment_candidates_v0 import enumerate_field_candidates, score_candidate
from casa.prisms.memory.sss_segment_v0 import format_segment, norm_word, verify_segment, vowel_count


def _hyp_from_parts(word: str, parts: list[str]) -> dict[str, Any]:
    w = norm_word(word)
    joined = "".join(parts)
    return {
        "word": w,
        "syllables": parts,
        "syllable_count": len(parts),
        "vowel_count": vowel_count(w),
        "join_ok": joined == w,
        "count_matches_vowels": len(parts) == vowel_count(w),
    }


def internal_reconcile(state: dict, word: str, attempt: list[str] | None = None) -> dict[str, Any] | None:
    """
    When inner checks fail, search among field candidates for one that passes verify.
    Discovered fix becomes abstract rule — not copied from canon.
    """
    w = norm_word(word)
    attempt = attempt or []
    before = format_segment(attempt) if attempt else ""
    candidates = enumerate_field_candidates(state, word)
    viable = [c for c in candidates if c.get("join_ok") and c.get("count_matches_vowels")]
    if not viable:
        return None
    best = max(viable, key=lambda c: float(c.get("field_score") or 0))
    after_parts = list(best["syllables"])
    after = format_segment(after_parts)
    if before == after:
        return None

    ver = verify_segment(_hyp_from_parts(w, after_parts))
    if not ver.get("ok"):
        return None

    rule_id = "rule.segment.vowel_nuclei"
    rule_hint = (
        f"на «{w}» было {len(attempt)} кусков при {vowel_count(w)} гласных; "
        f"склеивание дало {len(after_parts)} — столько же, сколько гласных в слове"
    )
    return {
        "word": w,
        "before": before,
        "after": after,
        "syllables": after_parts,
        "verify": ver,
        "rule_id": rule_id,
        "rule_hint": rule_hint,
        "source": "internal_reconcile",
        "field_score": best.get("field_score"),
        "candidates_tried": len(candidates),
    }
