#!/usr/bin/env python3
"""Multi-hypothesis W: competition before listen — field verify, no canon."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.prism_ids import PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL
from casa.domain.prism_wire import normalize_prisms, prism_memory, prism_hippo, prism_control, set_active_prism
from typing import Any

from casa.prisms.shared.codec_grid import Grid
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.field_decode import grapheme_votes_for_word
from casa.prisms.memory.segment import norm_word
from casa.prisms.memory.stack import _place_token
from casa.prisms.memory.vocab import listen_word, w_token
from casa.prisms.memory.word_candidates import enumerate_word_candidates


def q_token(word: str) -> str:
    return f"Q:{norm_word(word)}"


def w_hyp_token(word: str, segment: str) -> str:
    return f"Wh:{norm_word(word)}/{segment}"


def _clear_word_hyp(lat: dict, word: str) -> Grid:
    w = norm_word(word)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=[list(x) for x in lat["cells"]])
    for row in g.cells:
        row[:] = [
            t
            for t in row
            if not (t.startswith(f"Wh:{w}/") or t == q_token(w) or t == w_token(w))
        ]
    return g


def _replant_word_hypotheses(state: dict, word: str, segment_copies: dict[str, int]) -> None:
    w = norm_word(word)
    lattices = memory_lattices(state)
    lid = "L3_phrase"
    if lid not in lattices:
        return
    lat = lattices[lid]
    g = _clear_word_hyp(lat, w)
    g = _place_token(g, q_token(w), q_token(w), copies=2, radius=3)
    for segment, copies in segment_copies.items():
        if copies <= 0:
            continue
        tok = w_hyp_token(w, segment)
        g = _place_token(g, tok, tok, copies=int(copies), radius=3)
    lat["cells"] = g.cells
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def compete_word_hypotheses(state: dict, surface: str) -> dict[str, Any]:
    """Score syllable parses for one word chunk; pick field_focus (join_ok preferred)."""
    state = ensure_prisms(state)
    w = norm_word(surface)
    entries = enumerate_word_candidates(state, w)
    viable = [e for e in entries if e.get("join_ok")]
    babble = max(entries, key=lambda e: (e["field_score"], e["segment"]))
    field_focus = max(viable, key=lambda e: (e["field_score"], e["segment"])) if viable else babble

    post: dict[str, int] = {}
    for e in entries:
        post[e["segment"]] = 1 if not e.get("join_ok") else max(2, int(e["field_score"] // 6) + 2)
    post[field_focus["segment"]] = post.get(field_focus["segment"], 2) + 2
    _replant_word_hypotheses(state, w, post)

    gv = grapheme_votes_for_word(state, w)
    return {
        "word": w,
        "surface": w,
        "winner_segment": field_focus["segment"],
        "winner_syllables": field_focus["syllables"],
        "babble_segment": babble["segment"],
        "join_ok": field_focus.get("join_ok", False),
        "field_score": field_focus["field_score"],
        "grapheme_confidence": round(sum(gv.values()) / max(1, len(w)), 2),
        "competition": {
            "contenders": [
                {
                    "segment": e["segment"],
                    "field_score": e["field_score"],
                    "join_ok": e.get("join_ok"),
                    "source": e.get("source"),
                    "copies_after": post.get(e["segment"], 0),
                }
                for e in entries
            ],
            "viable_count": len(viable),
            "winner": field_focus["segment"],
        },
    }


def listen_word_field(
    state: dict,
    surface: str,
    *,
    scene_id: str | None = None,
    caption: str = "",
    copies: int = 3,
    bundle: dict | None = None,
    link_scene: bool = True,
) -> dict[str, Any]:
    """Compete W hypotheses, then imprint winner on L2."""
    comp = compete_word_hypotheses(state, surface)
    heard = listen_word(
        state,
        comp["word"],
        scene_id=scene_id,
        caption=caption,
        copies=copies,
        bundle=bundle,
        link_scene=link_scene,
    )
    return {**heard, "field_competition": comp}
