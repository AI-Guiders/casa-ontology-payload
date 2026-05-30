#!/usr/bin/env python3
"""Multi-cylinder SSS: cyl_memory + cyl_hippo + sleep consolidate."""

from __future__ import annotations

import json
import time
import unicodedata
from pathlib import Path
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_stack_v0 import (  # type: ignore
    _place_token,
    apply_z_compose_v0,
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
    """Migrate sss-only field_state → multi_cylinder_v1."""
    if state.get("cylinders") and state["cylinders"].get("cyl_memory"):
        return state
    sss = state.get("sss") or {}
    lattices = sss.get("lattices") or {}
    state["schema_version"] = "multi_cylinder_v1"
    state["cylinders"] = {
        "cyl_memory": {
            "subsystem": "sss",
            "stack": sss.get("stack") or "design/sss-lattice-stack.v0.json",
            "lattices": lattices,
            "active_lattice": sss.get("active_lattice") or "L0_grapheme",
        },
        "cyl_hippo": {
            "subsystem": "episodic",
            "lattices": {"H0_episode": empty_hippo_lattice()},
            "episodes": list((state.get("cylinders") or {}).get("cyl_hippo", {}).get("episodes") or []),
        },
    }
    state["sn"] = state.get("sn") or {
        "active_cylinder": "cyl_memory",
        "active_lattice": "L0_grapheme",
        "mode": "wake",
    }
    state["consolidation"] = state.get("consolidation") or {
        "last_sleep_tick": 0,
        "episodes_merged_total": 0,
    }
    return state


def memory_lattices(state: dict) -> dict[str, dict]:
    state = ensure_cylinders(state)
    mem = state["cylinders"]["cyl_memory"]
    if mem.get("lattices"):
        return mem["lattices"]
    return (state.get("sss") or {}).get("lattices") or {}


def hippo_episodes(state: dict) -> list[dict]:
    state = ensure_cylinders(state)
    return list(state["cylinders"]["cyl_hippo"].get("episodes") or [])


def concept_id_for_surface(bundle: dict, surface: str, *, lattice_id: str) -> str | None:
    surface = unicodedata.normalize("NFC", (surface or "").strip().lower())
    if not surface:
        return None
    prefix_map = {
        "L0_grapheme": "grapheme.",
        "L1_syllable": "syllable.",
        "L2_word": "lang.word.",
    }
    prefix = prefix_map.get(lattice_id, "")
    if not prefix and lattice_id.startswith("L2_word_"):
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


def append_episode(
    state: dict,
    *,
    cue: str,
    babble: str,
    correct: str,
    lattice_id: str,
    concept_id: str | None = None,
    bundle: dict | None = None,
) -> dict:
    state = ensure_cylinders(state)
    if bundle and not concept_id:
        concept_id = concept_id_for_surface(bundle, correct, lattice_id=lattice_id)

    ep = {
        "id": _now_id(),
        "cue": cue.strip()[:120],
        "babble": babble.strip()[:120],
        "correct": correct.strip()[:120],
        "lattice_id": lattice_id,
        "concept_id": concept_id,
        "consolidated": False,
        "kind": "surface",
    }
    hippo = state["cylinders"]["cyl_hippo"]
    hippo.setdefault("episodes", []).append(ep)

    h0 = hippo["lattices"]["H0_episode"]
    g = Grid(
        width=int(h0["width"]),
        height=int(h0["height"]),
        cells=[list(x) for x in h0["cells"]],
    )
    tok = f"T:{ep['id']}|{ep['cue'][:20]}|{ep['correct'][:20]}"
    g = _place_token(g, tok, tok, copies=2, radius=3)
    h0["cells"] = g.cells

    state["sn"] = {**(state.get("sn") or {}), "active_cylinder": "cyl_hippo", "mode": "wake"}
    state["field_version"] = int(state.get("field_version") or 0) + 1
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
        "lattice_id": "L2_word",
        "concept_id": concept_id_for_surface(bundle, word, lattice_id="L2_word") if bundle else None,
        "consolidated": False,
    }
    hippo = state["cylinders"]["cyl_hippo"]
    hippo.setdefault("episodes", []).append(ep)

    h0 = hippo["lattices"]["H0_episode"]
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

    state["sn"] = {**(state.get("sn") or {}), "active_cylinder": "cyl_hippo", "mode": "wake"}
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return ep


def _strengthen_rule(state: dict, rule_id: str, *, copies: int = 5) -> None:
    """Consolidate rule as R: token on memory L3 + hippo (intuition lives on field)."""
    from sss_stack_v0 import _place_token  # type: ignore

    sss = state.setdefault("sss", {})
    # mirror for debug/bench only — not read on hot path
    active = list(sss.get("active_segment_rules") or [])
    if rule_id not in active:
        active.insert(0, rule_id)
    sss["active_segment_rules"] = active

    rtok = f"R:{rule_id}"
    lattices = memory_lattices(state)

    lid = "L3_phrase"
    if lid in lattices:
        lat = lattices[lid]
        g = Grid(
            width=int(lat["width"]),
            height=int(lat["height"]),
            cells=[list(x) for x in lat["cells"]],
        )
        g = _place_token(g, rtok, rtok, copies=copies, radius=5)
        lat["cells"] = g.cells

    hippo = state["cylinders"]["cyl_hippo"]
    h0 = hippo["lattices"]["H0_episode"]
    g = Grid(
        width=int(h0["width"]),
        height=int(h0["height"]),
        cells=[list(x) for x in h0["cells"]],
    )
    g = _place_token(g, rtok, rtok, copies=max(2, copies // 2), radius=4)
    h0["cells"] = g.cells

    from sss_field_decode_v0 import rule_votes_from_field  # type: ignore

    sss.setdefault("rules", {})[rule_id] = {
        **sss.get("rules", {}).get(rule_id, {}),
        "votes": int(rule_votes_from_field(state).get(rule_id, 0)),
        "source": "field",
    }
    state["cylinders"]["cyl_memory"]["lattices"] = lattices
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
    nca_lattice_id: str = "L2_word",
) -> dict:
    """T_sleep: merge hippo episodes → cyl_memory; prune consolidated."""
    state = ensure_cylinders(state)
    stack = load_stack(stack_path)
    lattices = memory_lattices(state)
    hippo = state["cylinders"]["cyl_hippo"]
    episodes = hippo.get("episodes") or []
    merged: list[dict] = []
    pending = []

    for ep in episodes:
        if ep.get("consolidated"):
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
                    "attempt": ep.get("babble"),
                    "correct": ep.get("correct"),
                    "rule_hint": ep.get("rule_hint"),
                }
            )
            continue
        lid = str(ep.get("lattice_id") or "L1_syllable")
        cid = ep.get("concept_id")
        if not cid and bundle:
            cid = concept_id_for_surface(bundle, str(ep.get("correct") or ""), lattice_id=lid)
        if cid and _strengthen_concept(lattices, lid, str(cid), copies=strength):
            ep = {**ep, "consolidated": True, "merged_concept_id": cid}
            merged.append(
                {
                    "episode_id": ep.get("id"),
                    "kind": "surface",
                    "lattice_id": lid,
                    "concept_id": cid,
                    "cue": ep.get("cue"),
                    "correct": ep.get("correct"),
                }
            )
        else:
            pending.append(ep)

    compose = apply_z_compose_v0(lattices, bundle, stack)

    hippo["episodes"] = pending
    state["cylinders"]["cyl_memory"]["lattices"] = lattices
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
            from sss_nca_repair_v0 import nca_regrow_lattice  # type: ignore

            reg = nca_regrow_lattice(lattices[nca_lattice_id], nca_path, device="cpu")
            lattices[nca_lattice_id] = reg["lattice"]
            state["cylinders"]["cyl_memory"]["lattices"] = lattices
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
    }
    state["sn"] = {**(state.get("sn") or {}), "active_cylinder": "cyl_memory", "mode": "wake"}
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
    save_field_state(path, state, compact=compact)
