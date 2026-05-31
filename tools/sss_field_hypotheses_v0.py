#!/usr/bin/env python3
"""Multi-hypothesis competition on field: H:{word}/{segment} tokens on hippo."""

from __future__ import annotations

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from lattice_names_v1 import EPISODIC_SURFACE, PHRASES  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_field_decode_v0 import grapheme_votes_for_word, rule_votes_from_field, syllable_hits_from_field  # type: ignore
from sss_field_decode_v0 import active_rule_from_field  # type: ignore
from sss_segment_candidates_v0 import enumerate_field_candidates  # type: ignore
from sss_segment_v0 import format_segment, norm_word, parse_segment, verify_segment, vowel_count  # type: ignore
from sss_stack_v0 import _place_token  # type: ignore


def h_token(word: str, segment: str) -> str:
    return f"H:{norm_word(word)}/{segment}"


def parse_h_token(token: str) -> tuple[str, str] | None:
    if not token.startswith("H:"):
        return None
    rest = token[2:]
    if "/" not in rest:
        return None
    word, segment = rest.split("/", 1)
    return norm_word(word), segment


def _hippo_h0(state: dict) -> dict:
    state = ensure_prisms(state)
    lats = prism_hippo(state).setdefault("lattices", {})
    return lats[EPISODIC_SURFACE]


def _lattice_to_grid(lat: dict) -> Grid:
    return Grid(
        width=int(lat["width"]),
        height=int(lat["height"]),
        cells=[list(x) for x in lat["cells"]],
    )


def h_votes_for_word(state: dict, word: str) -> dict[str, int]:
    """segment_str → vote count from H: tokens on hippo + L3."""
    w = norm_word(word)
    prefix = f"H:{w}/"
    votes: dict[str, int] = {}
    lattices: list[dict] = [_hippo_h0(state)]
    l3 = memory_lattices(state).get(PHRASES)
    if l3:
        lattices.append(l3)
    for lat in lattices:
        for cell in lat.get("cells") or []:
            for t in cell:
                if t.startswith(prefix):
                    seg = t[len(prefix) :]
                    votes[seg] = votes.get(seg, 0) + 1
    return votes


def _clear_h_tokens(lat: dict, word: str) -> Grid:
    w = norm_word(word)
    prefix = f"H:{w}/"
    g = _lattice_to_grid(lat)
    for row in g.cells:
        row[:] = [t for t in row if not (t.startswith(prefix) or t == f"Q:{w}")]
    return g


def _replant_hypotheses(
    state: dict,
    word: str,
    segment_copies: dict[str, int],
    *,
    also_l3: bool = True,
) -> None:
    w = norm_word(word)
    h0 = _hippo_h0(state)
    g = _clear_h_tokens(h0, w)
    g = _place_token(g, f"Q:{w}", f"Q:{w}", copies=2, radius=4)
    for segment, copies in segment_copies.items():
        if copies <= 0:
            continue
        tok = h_token(w, segment)
        g = _place_token(g, tok, tok, copies=int(copies), radius=4)
    h0["cells"] = g.cells

    if also_l3:
        lattices = memory_lattices(state)
        lid = PHRASES
        if lid in lattices:
            lat = lattices[lid]
            g3 = _clear_h_tokens(lat, w)
            g3 = _place_token(g3, f"Q:{w}", f"Q:{w}", copies=1, radius=3)
            for segment, copies in segment_copies.items():
                if copies <= 0:
                    continue
                tok = h_token(w, segment)
                mirror = max(1, int(copies) // 2)
                g3 = _place_token(g3, tok, tok, copies=mirror, radius=3)
            lat["cells"] = g3.cells
            prism_memory(state)["lattices"] = lattices
            state.setdefault("sss", {})["lattices"] = lattices


def _hyp_payload(
    state: dict,
    word: str,
    syllables: list[str],
    *,
    rule_id: str | None,
    rule_votes: dict[str, int],
    field_score: float,
    segment: str,
) -> dict[str, Any]:
    w = norm_word(word)
    joined = "".join(syllables)
    gvotes = grapheme_votes_for_word(state, word)
    field_confidence = sum(gvotes.values()) / max(1, len(w))
    return {
        "word": w,
        "rule_id": rule_id,
        "syllables": syllables,
        "syllable_count": len(syllables),
        "vowel_count": vowel_count(w),
        "join_ok": joined == w,
        "count_matches_vowels": len(syllables) == vowel_count(w),
        "intuition_source": "field",
        "field_rule_votes": rule_votes,
        "field_grapheme_confidence": round(field_confidence, 2),
        "field_score": field_score,
        "segment_source": "field_competition",
        "segment": segment,
        "syllable_hits": [s for s, _ in syllable_hits_from_field(state, word)[:8]],
    }


def compete_hypotheses(state: dict, word: str) -> dict[str, Any]:
    """
    Plant competing H: tokens, verify each, suppress failed, boost viable/winner.
    Returns winning hypothesis dict + competition report.
    """
    state = ensure_prisms(state)
    w = norm_word(word)
    rule_id, rule_votes = active_rule_from_field(state)
    existing = h_votes_for_word(state, w)
    candidates = enumerate_field_candidates(state, w)

    merged: dict[str, dict[str, Any]] = {}
    for c in candidates:
        seg = format_segment(list(c["syllables"]))
        merged[seg] = {
            "syllables": list(c["syllables"]),
            "field_score": float(c.get("field_score") or 0),
            "h_votes_before": int(existing.get(seg, 0)),
        }
    for seg, hv in existing.items():
        if seg in merged:
            continue
        parts = parse_segment(seg)
        if parts and "".join(parts) == w:
            merged[seg] = {
                "syllables": parts,
                "field_score": 0.0,
                "h_votes_before": int(hv),
            }

    if not merged:
        parts = [w] if w else []
        seg = format_segment(parts)
        merged[seg] = {"syllables": parts, "field_score": 0.0, "h_votes_before": 0}

    entries: list[dict[str, Any]] = []
    for seg, data in merged.items():
        parts = list(data["syllables"])
        hyp = _hyp_payload(
            state,
            w,
            parts,
            rule_id=rule_id,
            rule_votes=rule_votes,
            field_score=float(data["field_score"]),
            segment=seg,
        )
        ver = verify_segment(hyp)
        entries.append(
            {
                **hyp,
                "verify": ver,
                "segment": seg,
                "h_votes_before": int(data["h_votes_before"]),
                "competition_score": float(data["field_score"]) + int(data["h_votes_before"]) * 2.0,
            }
        )

    viable = [e for e in entries if e["verify"]["ok"]]
    failed = [e for e in entries if not e["verify"]["ok"]]

    post_copies: dict[str, int] = {}
    for e in failed:
        post_copies[e["segment"]] = 1
    for e in viable:
        post_copies[e["segment"]] = max(2, int(e["field_score"] // 8) + 3)

    # Babble = сильнейший pull поля (может не пройти verify); tie → «перерез» с лишними слогами
    babble = max(
        entries,
        key=lambda e: (
            e["competition_score"],
            e["syllable_count"] - e["vowel_count"],
            e["segment"],
        ),
    )
    field_focus = max(viable, key=lambda e: (e["competition_score"], e["segment"])) if viable else babble
    post_copies[field_focus["segment"]] = post_copies.get(field_focus["segment"], 2) + 2

    _replant_hypotheses(state, w, post_copies)
    votes_after = h_votes_for_word(state, w)

    competition = {
        "cue": w,
        "planted": len(post_copies),
        "viable_count": len(viable),
        "failed_count": len(failed),
        "babble_segment": babble["segment"],
        "field_focus_segment": field_focus["segment"],
        "winner_votes_after": votes_after.get(field_focus["segment"], 0),
        "contenders": [
            {
                "segment": e["segment"],
                "field_score": e["field_score"],
                "h_votes_before": e["h_votes_before"],
                "inner_ok": e["verify"]["ok"],
                "copies_after": post_copies.get(e["segment"], 0),
            }
            for e in sorted(entries, key=lambda x: -x["competition_score"])
        ],
    }

    out = {k: v for k, v in babble.items() if k not in ("verify", "competition_score")}
    out["competition"] = competition
    out["alternatives"] = [
        {k: v for k, v in e.items() if k in ("segment", "field_score", "syllables", "verify")}
        for e in entries
        if e["segment"] != babble["segment"]
    ][:4]
    out["candidates_considered"] = len(entries)
    return out
