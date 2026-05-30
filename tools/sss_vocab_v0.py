#!/usr/bin/env python3
"""B2 vocabulary: W: tokens, scene links, read-aloud listen."""

from __future__ import annotations

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import re
import unicodedata
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from sss_cylinders_v0 import append_episode, ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import (  # type: ignore
    LEGACY_L2,
    concept_votes_l2,
    route_l2_lattice,
    sharding_config,
)
from sss_stack_v0 import _place_token, apply_z_compose_v0, decode_lattice, load_stack  # type: ignore


def norm_word(word: str) -> str:
    return unicodedata.normalize("NFC", (word or "").strip().lower())


def w_token(word: str) -> str:
    return f"W:{norm_word(word)}"


def scene_token(scene_id: str) -> str:
    return f"S:{scene_id}"


def link_token(scene_id: str, word: str) -> str:
    return f"L:{scene_id}|{norm_word(word)}"


def p_token(mark: str) -> str:
    """Punctuation mark on field (L3 + L0 grapheme anchor)."""
    return f"P:{mark}"


def punct_concept_id(mark: str) -> str:
    slug = {
        ".": "period",
        ",": "comma",
        "!": "exclam",
        "?": "question",
        ":": "colon",
        ";": "semicolon",
        "—": "emdash",
        "-": "hyphen",
        "«": "guillemet_open",
        "»": "guillemet_close",
        "…": "ellipsis",
        "...": "ellipsis_ascii",
        "(": "paren_open",
        ")": "paren_close",
        '"': "quote",
    }.get(mark)
    if slug is None:
        slug = "u" + "".join(f"{ord(ch):04x}" for ch in mark) if mark else "empty"
    return f"punct.{slug}"


def punct_votes_from_field(state: dict) -> dict[str, int]:
    votes: dict[str, int] = {}
    lattices = memory_lattices(ensure_prisms(state))
    for lat in lattices.values():
        for cell in lat.get("cells") or []:
            for t in cell:
                if t.startswith("P:"):
                    m = t[2:]
                    votes[m] = votes.get(m, 0) + 1
    hippo = prism_hippo(state)
    for lat in (hippo.get("lattices") or {}).values():
        for cell in lat.get("cells") or []:
            for t in cell:
                if t.startswith("P:"):
                    m = t[2:]
                    votes[m] = votes.get(m, 0) + 1
    return votes


def word_votes_from_field(state: dict) -> dict[str, int]:
    votes: dict[str, int] = {}
    lattices = memory_lattices(ensure_prisms(state))
    for lat in lattices.values():
        for cell in lat.get("cells") or []:
            for t in cell:
                if t.startswith("W:"):
                    w = t[2:]
                    votes[w] = votes.get(w, 0) + 1
    hippo = prism_hippo(state)
    for lat in (hippo.get("lattices") or {}).values():
        for cell in lat.get("cells") or []:
            for t in cell:
                if t.startswith("W:"):
                    w = t[2:]
                    votes[w] = votes.get(w, 0) + 1
    return votes


def concept_votes(state: dict, lattice_id: str, concept_id: str) -> int:
    if lattice_id == LEGACY_L2 or lattice_id.startswith("L2_word_"):
        votes, _ = concept_votes_l2(state, concept_id)
        return votes
    lattices = memory_lattices(ensure_prisms(state))
    lat = lattices.get(lattice_id) or {}
    dec = decode_lattice(lat, min_votes=1)
    for c in dec.get("concepts") or []:
        if str(c.get("concept_id")) == concept_id:
            return int(c.get("votes") or 0)
    return 0


def _strengthen_word_on_l2(
    state: dict,
    word: str,
    *,
    copies: int = 3,
) -> str:
    w = norm_word(word)
    cid = f"lang.word.{w}"
    cfg = sharding_config(state)
    if cfg.get("enabled", True):
        lid = route_l2_lattice(state, w)
    else:
        lid = LEGACY_L2
    lattices = memory_lattices(state)
    if lid not in lattices:
        return lid
    lat = lattices[lid]
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=copies, radius=5)
    g = _place_token(g, w_token(w), w_token(w), copies=max(2, copies), radius=4)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lid


def _listen_scene_on_l3(
    state: dict,
    scene_id: str,
    caption: str,
    words: list[str],
    *,
    copies: int = 2,
    punctuation: list[str] | None = None,
) -> None:
    lattices = memory_lattices(state)
    lid = "L3_phrase"
    if lid not in lattices:
        return
    lat = lattices[lid]
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    stok = scene_token(scene_id)
    g = _place_token(g, stok, stok, copies=copies, radius=4)
    cap_slug = re.sub(r"\s+", " ", caption.strip())[:40]
    g = _place_token(g, f"T3:{scene_id}", f"T3:{scene_id}|{cap_slug}", copies=max(1, copies - 1), radius=3)
    for w in words:
        ltok = link_token(scene_id, w)
        g = _place_token(g, ltok, ltok, copies=copies, radius=3)
    for mark in punctuation or []:
        ptok = p_token(mark)
        g = _place_token(g, ptok, ptok, copies=max(1, copies - 1), radius=3)
        g = _place_token(g, f"Lp:{scene_id}|{mark}", f"Lp:{scene_id}|{mark}", copies=copies, radius=3)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def _strengthen_punct_on_field(state: dict, mark: str, *, copies: int = 2) -> None:
    lattices = memory_lattices(state)
    ptok = p_token(mark)
    cid = punct_concept_id(mark)
    for lid in ("L3_phrase", "L0_grapheme"):
        if lid not in lattices:
            continue
        lat = lattices[lid]
        g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
        g = _place_token(g, ptok, ptok, copies=copies, radius=4)
        if lid == "L0_grapheme" and len(mark) == 1:
            g = _place_token(g, f"C:grapheme.{mark}", f"C:grapheme.{mark}", copies=max(1, copies - 1), radius=3)
        if lid == "L3_phrase":
            g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=max(1, copies - 1), radius=3)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def listen_punct(
    state: dict,
    mark: str,
    *,
    scene_id: str | None = None,
    caption: str = "",
    copies: int = 2,
    link_scene: bool = True,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    m = mark.strip()
    if not m:
        return {"mark": "", "p_votes": 0}
    _strengthen_punct_on_field(state, m, copies=copies)
    if scene_id and link_scene:
        _listen_scene_on_l3(state, scene_id, caption, [], copies=max(1, copies - 1), punctuation=[m])
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "mark": m,
        "concept_id": punct_concept_id(m),
        "p_votes": punct_votes_from_field(state).get(m, 0),
        "scene_id": scene_id,
    }


def listen_word(
    state: dict,
    word: str,
    *,
    scene_id: str | None = None,
    caption: str = "",
    copies: int = 3,
    bundle: dict | None = None,
    link_scene: bool = True,
) -> dict[str, Any]:
    """Read-aloud one word: imprint on L2 + optional scene link + episodic trace."""
    state = ensure_prisms(state)
    w = norm_word(word)
    lid = _strengthen_word_on_l2(state, w, copies=copies)
    if scene_id and link_scene:
        _listen_scene_on_l3(state, scene_id, caption, [w], copies=max(2, copies - 1))

    ep = append_episode(
        state,
        cue=caption or scene_id or w,
        surface_attempt="",
        correct=w,
        lattice_id=lid,
        concept_id=f"lang.word.{w}",
        bundle=bundle,
    )
    cv, _ = concept_votes_l2(state, f"lang.word.{w}")
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "word": w,
        "concept_id": f"lang.word.{w}",
        "lattice_id": lid,
        "w_votes": word_votes_from_field(state).get(w, 0),
        "c_votes": cv,
        "episode_id": ep.get("id"),
        "scene_id": scene_id,
    }


def listen_scene(
    state: dict,
    scene: dict,
    *,
    copies: int = 3,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """One story frame: caption + all words (like picture + labels)."""
    sid = str(scene.get("id") or "")
    caption = str(scene.get("caption") or "")
    words = [norm_word(w) for w in (scene.get("words") or []) if str(w).strip()]
    punct = [str(p) for p in (scene.get("punctuation") or []) if str(p).strip()]
    _listen_scene_on_l3(state, sid, caption, words, copies=copies, punctuation=punct)
    heard: list[dict] = []
    for w in words:
        heard.append(
            listen_word(
                state,
                w,
                scene_id=sid,
                caption=caption,
                copies=copies,
                bundle=bundle,
                link_scene=False,
            )
        )
    heard_punct: list[dict] = []
    for mark in punct:
        heard_punct.append(
            listen_punct(state, mark, scene_id=sid, caption=caption, copies=max(1, copies - 1), link_scene=False)
        )
    return {"scene_id": sid, "caption": caption, "words": heard, "punctuation": heard_punct}


def recall_words_for_scene(state: dict, scene_id: str) -> list[dict[str, Any]]:
    """Recall vocabulary linked to scene — field only, no canon lookup."""
    state = ensure_prisms(state)
    wvotes = word_votes_from_field(state)
    prefix = f"L:{scene_id}|"
    linked: list[str] = []
    lattices = memory_lattices(state)
    l3 = lattices.get("L3_phrase") or {}
    for cell in l3.get("cells") or []:
        for t in cell:
            if t.startswith(prefix):
                linked.append(t[len(prefix) :])
    linked = list(dict.fromkeys(linked))
    ranked: list[dict[str, Any]] = []
    for w in linked:
        cid = f"lang.word.{w}"
        cv, _ = concept_votes_l2(state, cid)
        ranked.append(
            {
                "word": w,
                "w_votes": wvotes.get(w, 0),
                "c_votes": cv,
                "score": wvotes.get(w, 0) + cv,
            }
        )
    ranked.sort(key=lambda x: (-x["score"], x["word"]))
    return ranked


def recall_word_best(state: dict, scene_id: str) -> dict[str, Any] | None:
    ranked = recall_words_for_scene(state, scene_id)
    return ranked[0] if ranked else None


def apply_story_compose(state: dict, bundle: dict, *, stack_path: str | None = None) -> dict:
    """Refresh z_compose after new word edges from skazka bundle."""
    lattices = memory_lattices(ensure_prisms(state))
    stack = load_stack(stack_path)
    report = apply_z_compose_v0(lattices, bundle, stack)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return report
