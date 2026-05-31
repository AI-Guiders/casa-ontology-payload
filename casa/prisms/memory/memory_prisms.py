#!/usr/bin/env python3
"""Multi-prism SSS: prism_memory + prism_hippo + sleep consolidate."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
import time
import unicodedata
from pathlib import Path
from typing import Any

from casa.prisms.shared.prism_state import (
    PRISM_HIPPO,
    PRISM_MEMORY,
    SCHEMA_CURRENT,
    normalize_prisms,
    prism_hippo,
    prism_memory,
    set_active_prism,
)
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.lattice_names_v1 import ALPHABET_RU, ALPHABET_UK, ALPHABET_EN, EPISODIC_SURFACE, LEXICON_RU, PHRASES
from casa.prisms.memory.stack import (
    _place_token,
    apply_z_compose,
    decode_lattice,
    load_stack,
)


def _now_id() -> str:
    return f"ep-{int(time.time() * 1000) % 10_000_000}"


def empty_hippo_lattice(*, width: int = 32, height: int = 32) -> dict:
    n = width * height
    return {
        "z_level": 0,
        "width": width,
        "height": height,
        "cells": [[] for _ in range(n)],
        "concept_prefix": "episodic.",
    }


def ensure_cylinders(state: dict) -> dict:
    """Ensure prism blocks (legacy name ensure_cylinders). Reads old cyl_* on load."""
    normalize_prisms(state)
    hip = prism_hippo(state)
    hip.setdefault("subsystem", "episodic")
    hip.setdefault("lattices", {})
    hip["lattices"].setdefault(EPISODIC_SURFACE, empty_hippo_lattice())
    hip.setdefault("episodes", list(hip.get("episodes") or []))

    mem = prism_memory(state)
    if mem.get("lattices"):
        return state
    sss = state.get("sss") or {}
    lattices = sss.get("lattices") or {}
    state["schema_version"] = SCHEMA_CURRENT
    mem["subsystem"] = "sss"
    mem["stack"] = sss.get("stack") or "design/sss-lattice-stack.toml"
    mem["lattices"] = lattices
    mem["active_lattice"] = sss.get("active_lattice") or ALPHABET_RU
    state["sn"] = {
        **(state.get("sn") or {}),
        "active_lattice": mem["active_lattice"],
        "mode": (state.get("sn") or {}).get("mode") or "wake",
    }
    set_active_prism(state, PRISM_MEMORY)
    state["consolidation"] = state.get("consolidation") or {
        "last_sleep_tick": 0,
        "episodes_merged_total": 0,
    }
    state.setdefault("sss", {})["lattices"] = lattices
    return state


ensure_prisms = ensure_cylinders


def memory_lattices(state: dict) -> dict[str, dict]:
    state = ensure_cylinders(state)
    mem = prism_memory(state)
    if mem.get("lattices"):
        return mem["lattices"]
    return (state.get("sss") or {}).get("lattices") or {}


def hippo_episodes(state: dict) -> list[dict]:
    state = ensure_cylinders(state)
    return list(prism_hippo(state).get("episodes") or [])


def concept_id_for_surface(bundle: dict, surface: str, *, lattice_id: str) -> str | None:
    surface = unicodedata.normalize("NFC", (surface or "").strip().lower())
    if not surface:
        return None
    prefix_map = {
        ALPHABET_RU: "grapheme.cyrl.",
        ALPHABET_EN: "grapheme.latn.",
        ALPHABET_UK: "grapheme.cyrl.",
        "syllables-ru": "syllable.",
        "syllables-en": "syllable.",
    }
    prefix = prefix_map.get(lattice_id, "")
    if not prefix and (lattice_id.startswith("lexicon-") or lattice_id == LEXICON_RU):
        prefix = "lang.word."
    for c in bundle.get("claims") or []:
        cid = str(c.get("concept_id") or "")
        if not cid.startswith(prefix):
            continue
        tail = cid.split(".", 1)[-1]
        slots = c.get("slots") or {}
        for key in ("letter", "syllable", "word"):
            if unicodedata.normalize("NFC", str(slots.get(key) or "").lower()) == surface:
                return cid
        if tail.lower() == surface or tail.lower().endswith(surface):
            return cid
    if prefix == "syllable.":
        return f"syllable.{surface}"
    if prefix == "grapheme." and len(surface) == 1:
        return f"grapheme.{surface}"
    if prefix == "lang.word.":
        return f"lang.word.{surface}"
    return None


def _episodic_surface_lattice(hippo: dict) -> dict:
    lats = hippo.setdefault("lattices", {})
    return lats.setdefault(EPISODIC_SURFACE, empty_hippo_lattice())


def _register_episode_on_h0(state: dict, ep: dict, *, token_suffix: str = "") -> None:
    hippo = prism_hippo(state)
    h0 = _episodic_surface_lattice(hippo)
    g = Grid(
        width=int(h0["width"]),
        height=int(h0["height"]),
        cells=[list(x) for x in h0["cells"]],
    )
    cue = str(ep.get("cue") or "")[:20]
    tail = str(ep.get("correct") or ep.get("question") or "")[:20]
    tok = f"T:{ep['id']}|{cue}|{tail}{token_suffix}"
    g = _place_token(g, tok, tok, copies=2, radius=3)
    h0["cells"] = g.cells
    set_active_prism(state, PRISM_HIPPO)
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake"}
    state["field_version"] = int(state.get("field_version") or 0) + 1


def append_episode(
    state: dict,
    *,
    cue: str,
    surface_attempt: str,
    correct: str,
    lattice_id: str,
    concept_id: str | None = None,
    bundle: dict | None = None,
    scene: str = "",
    correction_kind: str | None = None,
    pending: bool = False,
    structure_tag: str | None = None,
    min_recurrence: int = 1,
) -> dict:
    state = ensure_cylinders(state)
    if bundle and not concept_id:
        concept_id = concept_id_for_surface(bundle, correct, lattice_id=lattice_id)

    ep = {
        "id": _now_id(),
        "cue": cue.strip()[:120],
        "surface_attempt": surface_attempt.strip()[:120],
        "correct": correct.strip()[:120],
        "lattice_id": lattice_id,
        "concept_id": concept_id,
        "consolidated": False,
        "kind": "surface",
        "scene": (scene or "").strip()[:240],
        "correction_kind": correction_kind,
        "pending": bool(pending),
        "structure_tag": (structure_tag or "").strip()[:64] or None,
        "recurrence_seen": 0,
        "min_recurrence": max(1, int(min_recurrence)),
    }
    hippo = prism_hippo(state)
    hippo.setdefault("episodes", []).append(ep)
    _register_episode_on_h0(state, ep)
    return ep


def append_question_episode(
    state: dict,
    *,
    cue: str,
    surface_attempt: str,
    question: str,
    scene: str = "",
    options: list[str] | None = None,
    correction_kind: str = "lexical_ask",
) -> dict:
    """Lexical ask — pending until child answers; no lemma strengthen on first sleep."""
    state = ensure_cylinders(state)
    ep = {
        "id": _now_id(),
        "kind": "question",
        "cue": cue.strip()[:120],
        "surface_attempt": surface_attempt.strip()[:120],
        "question": question.strip()[:240],
        "scene": (scene or "").strip()[:240],
        "options": [str(o).strip()[:64] for o in (options or [])][:8],
        "correction_kind": correction_kind,
        "consolidated": False,
        "pending": True,
    }
    hippo = prism_hippo(state)
    hippo.setdefault("episodes", []).append(ep)
    _register_episode_on_h0(state, ep, token_suffix="|Q")
    return ep


def append_hint_episode(
    state: dict,
    *,
    cue: str,
    surface_attempt: str,
    hint: str,
    correction_kind: str = "wait_prefix",
) -> dict:
    """Prefix incomplete — hippo hint only, no sleep lemma merge."""
    state = ensure_cylinders(state)
    ep = {
        "id": _now_id(),
        "kind": "hint",
        "cue": cue.strip()[:120],
        "surface_attempt": surface_attempt.strip()[:120],
        "hint": hint.strip()[:240],
        "correction_kind": correction_kind,
        "consolidated": False,
        "pending": True,
    }
    hippo = prism_hippo(state)
    hippo.setdefault("episodes", []).append(ep)
    _register_episode_on_h0(state, ep, token_suffix="|H")
    return ep


def append_rule_episode(
    state: dict,
    *,
    word: str,
    attempt: str,
    correct: str,
    rule_id: str,
    rule_hint: str = "",
    bundle: dict | None = None,
) -> dict:
    """Teacher correction with rule: hypothesis wrong → episodic + rule anchor."""
    state = ensure_cylinders(state)
    ep = {
        "id": _now_id(),
        "kind": "rule",
        "cue": word.strip()[:120],
        "babble": attempt.strip()[:120],
        "correct": correct.strip()[:120],
        "rule_id": rule_id,
        "rule_hint": rule_hint.strip()[:240],
        "lattice_id": LEXICON_RU,
        "concept_id": concept_id_for_surface(bundle, word, lattice_id=LEXICON_RU) if bundle else None,
        "consolidated": False,
    }
    hippo = prism_hippo(state)
    hippo.setdefault("episodes", []).append(ep)

    h0 = _episodic_surface_lattice(hippo)
    g = Grid(
        width=int(h0["width"]),
        height=int(h0["height"]),
        cells=[list(x) for x in h0["cells"]],
    )
    tok = f"T:{ep['id']}|{ep['cue'][:12]}|{ep['correct'][:12]}"
    g = _place_token(g, tok, tok, copies=2, radius=3)
    rtok = f"R:{rule_id}"
    g = _place_token(g, rtok, rtok, copies=3, radius=4)
    h0["cells"] = g.cells

    set_active_prism(state, PRISM_HIPPO)
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake"}
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return ep


def _strengthen_rule(state: dict, rule_id: str, *, copies: int = 5) -> None:
    """Consolidate rule as R: token on memory L3 + hippo (intuition lives on field)."""
    from casa.prisms.memory.stack import _place_token

    sss = state.setdefault("sss", {})
    # mirror for debug/bench only — not read on hot path
    active = list(sss.get("active_segment_rules") or [])
    if rule_id not in active:
        active.insert(0, rule_id)
    sss["active_segment_rules"] = active

    rtok = f"R:{rule_id}"
    lattices = memory_lattices(state)

    lid = PHRASES
    if lid in lattices:
        lat = lattices[lid]
        g = Grid(
            width=int(lat["width"]),
            height=int(lat["height"]),
            cells=[list(x) for x in lat["cells"]],
        )
        g = _place_token(g, rtok, rtok, copies=copies, radius=5)
        lat["cells"] = g.cells

    hippo = prism_hippo(state)
    h0 = _episodic_surface_lattice(hippo)
    g = Grid(
        width=int(h0["width"]),
        height=int(h0["height"]),
        cells=[list(x) for x in h0["cells"]],
    )
    g = _place_token(g, rtok, rtok, copies=max(2, copies // 2), radius=4)
    h0["cells"] = g.cells

    from casa.prisms.memory.field_decode import rule_votes_from_field

    sss.setdefault("rules", {})[rule_id] = {
        **sss.get("rules", {}).get(rule_id, {}),
        "votes": int(rule_votes_from_field(state).get(rule_id, 0)),
        "source": "field",
    }
    prism_memory(state)["lattices"] = lattices
    sss["lattices"] = lattices


def _strengthen_concept(lattices: dict[str, dict], lattice_id: str, concept_id: str, *, copies: int) -> bool:
    if lattice_id not in lattices or not concept_id:
        return False
    lat = lattices[lattice_id]
    g = Grid(
        width=int(lat["width"]),
        height=int(lat["height"]),
        cells=[list(x) for x in lat["cells"]],
    )
    tok = f"C:{concept_id}"
    g = _place_token(g, tok, tok, copies=copies, radius=4)
    lat["cells"] = g.cells
    return True


def run_sleep(
    state: dict,
    bundle: dict,
    *,
    stack_path: Path | None = None,
    strength: int = 4,
    nca_model_path: Path | None = None,
    nca_lattice_id: str = LEXICON_RU,
    replay_k: int = 0,
    replay_value_weight: float = 0.0,
) -> dict:
    """T_sleep: merge hippo episodes → prism_memory; prune consolidated."""
    state = ensure_cylinders(state)
    from casa.prisms.hippo.sleep_replay import SleepReplayConfig, prepare_sleep_replay

    replay_report = prepare_sleep_replay(
        state,
        SleepReplayConfig(replay_k=replay_k, value_weight=replay_value_weight),
        bundle=bundle,
    )
    stack = load_stack(stack_path)
    lattices = memory_lattices(state)
    hippo = prism_hippo(state)
    episodes = hippo.get("episodes") or []
    merged: list[dict] = []
    pending = []

    for ep in episodes:
        if ep.get("consolidated"):
            continue
        if ep.get("pending") or ep.get("kind") in ("question", "hint"):
            pending.append(ep)
            continue
        if ep.get("kind") == "rule" and ep.get("rule_id"):
            rid = str(ep["rule_id"])
            _strengthen_rule(state, rid, copies=strength + 1)
            ep = {**ep, "consolidated": True, "merged_rule_id": rid}
            merged.append(
                {
                    "episode_id": ep.get("id"),
                    "kind": "rule",
                    "rule_id": rid,
                    "cue": ep.get("cue"),
                    "attempt": ep.get("surface_attempt") or ep.get("babble"),
                    "correct": ep.get("correct"),
                    "rule_hint": ep.get("rule_hint"),
                }
            )
            continue
        lid = str(ep.get("lattice_id") or "L1_syllable")
        cid = ep.get("concept_id")
        if not cid and bundle:
            cid = concept_id_for_surface(bundle, str(ep.get("correct") or ""), lattice_id=lid)
        min_rec = max(1, int(ep.get("min_recurrence") or 1))
        seen = int(ep.get("recurrence_seen") or 0) + 1
        ep = {**ep, "recurrence_seen": seen}
        if seen < min_rec:
            pending.append(ep)
            continue
        extract_rep = None
        if cid and str(cid).startswith("math.op.") and bundle:
            from casa.prisms.memory.f0_stack import mint_operator_denotes_from_episode

            extract_rep = mint_operator_denotes_from_episode(
                lattices,
                lattice_id=lid,
                cue=str(ep.get("cue") or ""),
                concept_id=str(cid),
                bundle=bundle,
                copies=strength,
            )
        if cid and _strengthen_concept(lattices, lid, str(cid), copies=strength):
            ep = {**ep, "consolidated": True, "merged_concept_id": cid}
            item = {
                "episode_id": ep.get("id"),
                "kind": "surface",
                "lattice_id": lid,
                "concept_id": cid,
                "cue": ep.get("cue"),
                "correct": ep.get("correct"),
                "correction_kind": ep.get("correction_kind"),
                "scene": ep.get("scene"),
            }
            if extract_rep:
                item["extract"] = extract_rep
            merged.append(item)
        else:
            pending.append(ep)

    compose = apply_z_compose(lattices, bundle, stack)

    hippo["episodes"] = pending
    prism_memory(state)["lattices"] = lattices
    state["sss"] = {
        **(state.get("sss") or {}),
        "lattices": lattices,
        "last_compose": compose,
    }
    cons = state.setdefault("consolidation", {})
    cons["last_sleep_tick"] = int(state.get("field_version") or 0) + 1
    cons["episodes_merged_total"] = int(cons.get("episodes_merged_total") or 0) + len(merged)
    nca_report = None
    nca_path = nca_model_path
    if nca_path is None:
        raw = (state.get("nca") or {}).get("model_path")
        if raw:
            nca_path = Path(str(raw))
    if nca_path is not None and nca_path.exists() and nca_lattice_id in lattices:
        try:
            from casa.prisms.memory.nca_repair import nca_regrow_lattice

            reg = nca_regrow_lattice(lattices[nca_lattice_id], nca_path, device="cpu")
            lattices[nca_lattice_id] = reg["lattice"]
            prism_memory(state)["lattices"] = lattices
            state.setdefault("sss", {})["lattices"] = lattices
            nca_report = {"mode": "regrow", "lattice_id": nca_lattice_id, **{k: v for k, v in reg.items() if k != "lattice"}}
        except Exception as exc:  # noqa: BLE001 — sleep must not fail on optional NCA
            nca_report = {"error": str(exc), "lattice_id": nca_lattice_id}

    cons["last_sleep"] = {
        "merged": len(merged),
        "pending": len(pending),
        "z_compose": compose.get("count"),
        "items": merged,
        "nca": nca_report,
        "replay": replay_report,
    }
    set_active_prism(state, PRISM_MEMORY)
    state["sn"] = {**(state.get("sn") or {}), "mode": "wake"}
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return cons["last_sleep"]


def episode_vote_for_cue(state: dict, bundle: dict, cue: str, lattice_id: str, concept_id: str) -> int:
    lattices = memory_lattices(state)
    if lattice_id not in lattices:
        return 0
    dec = decode_lattice(lattices[lattice_id], min_votes=1)
    for c in dec.get("concepts") or []:
        if str(c.get("concept_id")) == concept_id:
            return int(c.get("votes") or 0)
    return 0


def save_state(path: Path, state: dict, *, compact: bool = False) -> None:
    """Legacy alias — persists full runtime (field + agent tier when present)."""
    from casa.prisms.shared.store_persist import save_runtime_state

    save_runtime_state(path.parent, state, compact=compact, force=True)
