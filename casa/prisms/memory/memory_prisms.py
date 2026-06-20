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

from casa.domain.prism_ids import PRISM_HIPPO, PRISM_MEMORY, SCHEMA_CURRENT
from casa.domain.prism_wire import (
    normalize_prisms,
    prism_hippo,
    prism_memory,
    set_active_prism,
)
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.lattice_names_v1 import (
    ALPHABET_RU,
    ALPHABET_UK,
    ALPHABET_EN,
    EPISODIC_SURFACE,
    LEXICON_RU,
    PHRASES,
    SYLLABLES_RU,
    canonical_lattice_id,
)
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

    if not state.get("_multi_prism_bootstrapped"):
        state["_multi_prism_bootstrapped"] = True
        from casa.prisms.memory.prism_spawn import ensure_multi_prism_bootstrap

        ensure_multi_prism_bootstrap(state)

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
    if not (state.get("sn") or {}).get("active_prism"):
        set_active_prism(state, PRISM_MEMORY)
    state["consolidation"] = state.get("consolidation") or {
        "last_sleep_tick": 0,
        "episodes_merged_total": 0,
    }
    state.setdefault("sss", {})["lattices"] = lattices
    return state


ensure_prisms = ensure_cylinders


def set_content_lattice(
    state: dict,
    lattice_id: str,
    lattice: dict,
    *,
    write_context: str = "hot",
) -> None:
    """Write one lattice to its owning content prism."""
    from casa.domain.content_prism_split import lattice_content_prism_target
    from casa.domain.prism_ids import PRISM_MEMORY

    target = lattice_content_prism_target(lattice_id) or PRISM_MEMORY
    import_lattice_into_prism(state, target, lattice_id, lattice, write_context=write_context)


def content_prism_lattices(state: dict, prism_id: str | None = None) -> dict[str, dict]:
    """Lattices for one content prism (no cross-prism merge)."""
    state = ensure_cylinders(state)
    from casa.domain.prism_ids import PRISM_MEMORY
    from casa.domain.prism_wire import active_prism_id, prism_memory, prism_supports_lattices, prisms

    pid = prism_id or active_prism_id(state) or PRISM_MEMORY
    if not prism_supports_lattices(state, pid):
        pid = PRISM_MEMORY
    if pid == PRISM_MEMORY:
        lats = dict(prism_memory(state).get("lattices") or {})
        if lats:
            return lats
        return dict((state.get("sss") or {}).get("lattices") or {})
    block = prisms(state).get(pid) or {}
    return dict(block.get("lattices") or {})


def merged_content_lattices(state: dict) -> dict[str, dict]:
    """All content-prism lattices (runtime tick/sleep/predict)."""
    from casa.prisms.memory.prism_spawn import list_content_prism_ids

    state = ensure_cylinders(state)
    out: dict[str, dict] = {}
    for pid in list_content_prism_ids(state):
        for lid, lat in content_prism_lattices(state, pid).items():
            out[lid] = lat
    return out


def persist_content_lattices(
    state: dict,
    lattices: dict[str, dict],
    *,
    write_context: str = "hot",
) -> None:
    """Write lattice map back to owning content prisms (post split)."""
    from casa.domain.content_prism_split import lattice_content_prism_target
    from casa.domain.prism_ids import PRISM_MEMORY
    from casa.prisms.memory.write_gate import memory_write_allowed

    mem: dict[str, dict] = {}
    for lid, lat in lattices.items():
        target = lattice_content_prism_target(lid) or PRISM_MEMORY
        if target == PRISM_MEMORY:
            mem[lid] = lat
        if memory_write_allowed(state, lid, context=write_context):
            if target != PRISM_MEMORY:
                import_lattice_into_prism(state, target, lid, lat, write_context=write_context)
    prism_memory(state)["lattices"] = mem
    state.setdefault("sss", {})["lattices"] = dict(mem)


def memory_lattices(state: dict, prism_id: str | None = None) -> dict[str, dict]:
    if prism_id is not None:
        return content_prism_lattices(state, prism_id)
    return merged_content_lattices(state)


def import_lattice_into_prism(
    state: dict,
    prism_id: str,
    lattice_id: str,
    lattice: dict,
    *,
    write_context: str = "hot",
) -> None:
    """Place decoded lattice into a content prism (multi-prism import from ltm/)."""
    from casa.prisms.memory.write_gate import assert_memory_write_allowed

    assert_memory_write_allowed(state, lattice_id, context=write_context)
    from casa.prisms.memory.prism_spawn import list_content_prism_ids, spawn_prism
    from casa.domain.prism_ids import PRISM_KIND_CONTENT, PRISM_MEMORY
    from casa.domain.prism_wire import (
        prism_block,
        prism_memory,
        prism_supports_lattices,
        prisms,
    )

    state = ensure_cylinders(state)
    pid = prism_id or PRISM_MEMORY
    if pid != PRISM_MEMORY and pid not in prisms(state):
        spawn_prism(state, pid, kind=PRISM_KIND_CONTENT)
    if pid not in list_content_prism_ids(state) and pid != PRISM_MEMORY:
        pid = PRISM_MEMORY
    if pid == PRISM_MEMORY or not prism_supports_lattices(state, pid):
        lats = prism_memory(state).setdefault("lattices", {})
        lats[lattice_id] = lattice
        state.setdefault("sss", {})["lattices"] = lats
        return
    block = prism_block(state, pid)
    block.setdefault("lattices", {})[lattice_id] = lattice


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


def _normalize_hippo_lattice_cells(lat: dict, *, default_w: int = 32, default_h: int = 32) -> dict:
    """Ensure cells length matches width×height (thin field_state may store cells: [])."""
    w = int(lat.get("width") or default_w)
    h = int(lat.get("height") or default_h)
    n = w * h
    cells = lat.get("cells")
    if not isinstance(cells, list) or len(cells) != n:
        old = cells if isinstance(cells, list) else []
        lat["width"] = w
        lat["height"] = h
        lat["cells"] = [
            list(old[i]) if i < len(old) and isinstance(old[i], list) else [] for i in range(n)
        ]
    return lat


def _episodic_surface_lattice(hippo: dict) -> dict:
    lats = hippo.setdefault("lattices", {})
    lat = lats.get(EPISODIC_SURFACE)
    if lat is None:
        return lats.setdefault(EPISODIC_SURFACE, empty_hippo_lattice())
    return _normalize_hippo_lattice_cells(lat)


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
    links: list[dict[str, Any]] | None = None,
    form_extract_allowed: bool = False,
    allow_teacher_links: bool = False,
    crosslink_hypotheses: list[dict[str, Any]] | None = None,
    episode_source: str = "wake",
    bind_class: str | None = None,
) -> dict | None:
    state = ensure_cylinders(state)
    if episode_source == "ingest":
        from casa.prisms.memory.ingest_episodic import should_record_ingest_episode

        if not should_record_ingest_episode(
            state,
            correction_kind=correction_kind,
            scene=scene,
        ):
            return None
    if bundle and not concept_id:
        concept_id = concept_id_for_surface(bundle, correct, lattice_id=lattice_id)

    from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
    from casa.prisms.shared.memory_layer_names import memory_layer_for_lattice_id

    lattice_id = canonical_lattice_id(lattice_id)
    semantic_layer = memory_layer_for_lattice_id(lattice_id)

    from casa.domain.episode_bind import infer_bind_class

    resolved_bind = bind_class or infer_bind_class(
        structure_tag=structure_tag,
        scene=scene,
        concept_id=concept_id,
        correct=correct,
        kind="surface",
    )

    ep = {
        "id": _now_id(),
        "cue": cue.strip()[:120],
        "surface_attempt": surface_attempt.strip()[:120],
        "correct": correct.strip()[:120],
        "lattice_id": lattice_id,
        "semantic_layer": semantic_layer,
        "concept_id": concept_id,
        "bind_class": resolved_bind,
        "consolidated": False,
        "kind": "surface",
        "scene": (scene or "").strip()[:240],
        "correction_kind": correction_kind,
        "pending": bool(pending),
        "structure_tag": (structure_tag or "").strip()[:64] or None,
        "recurrence_seen": 0,
        "min_recurrence": max(1, int(min_recurrence)),
    }
    if form_extract_allowed:
        ep["form_extract_allowed"] = True
    if allow_teacher_links:
        ep["allow_teacher_links"] = True
    if crosslink_hypotheses:
        ep["crosslink_hypotheses"] = [
            {
                "relation": str(x.get("relation") or "denotes"),
                "dst": str(x.get("dst") or ""),
            }
            for x in crosslink_hypotheses[:12]
            if str(x.get("dst") or "").startswith("math.")
        ]
    if links:
        ep["links"] = [
            {
                "src": str(x.get("src") or ""),
                "relation": str(x.get("relation") or x.get("rel") or ""),
                "dst": str(x.get("dst") or ""),
            }
            for x in links[:12]
            if x.get("src") and (x.get("relation") or x.get("rel")) and x.get("dst")
        ]
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
    persist_content_lattices(state, lattices)


def _strengthen_concept(
    lattices: dict[str, dict],
    lattice_id: str,
    concept_id: str,
    *,
    copies: int,
    state: dict | None = None,
    write_context: str = "sleep_merge",
) -> bool:
    if state is not None:
        from casa.prisms.memory.write_gate import memory_write_allowed

        if not memory_write_allowed(state, lattice_id, context=write_context):
            return False
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
    bundle: dict | None = None,
    *,
    stack_path: Path | None = None,
    strength: int = 4,
    nca_model_path: Path | None = None,
    nca_lattice_id: str = LEXICON_RU,
    replay_k: int = 0,
    replay_value_weight: float = 0.0,
    store_dir: Path | None = None,
    compact_persist: bool | None = None,
    max_episodes: int | None = None,
) -> dict:
    """T_sleep: merge hippo episodes → prism_memory; prune consolidated.

    When ``max_episodes`` is set, consolidate at most that many eligible episodes
    (FIFO). F0 emergent passes and ``z_compose`` run only when the queue is drained
    in this call (full sleep or last batch). Kernel maintain + compact_persist still
    run when ``store_dir`` is set (ADR-0023 batched sleep).
    """
    bundle = bundle or {"claims": [], "graph": {"edges": []}}
    state = ensure_cylinders(state)
    from casa.domain.load_governor import cognitive_load_from_state, retire_stuck_surprise_episodes

    load_rep = cognitive_load_from_state(state)
    overload_retire = retire_stuck_surprise_episodes(state, overloaded=bool(load_rep.get("overloaded")))
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
    pending: list[dict] = []
    immutable_skipped: list[dict[str, Any]] = []
    consolidate_budget = max_episodes
    consolidated_this_call = 0
    budget_starved = 0

    for ep in episodes:
        if ep.get("consolidated"):
            continue
        if ep.get("pending") or ep.get("kind") in ("question", "hint"):
            pending.append(ep)
            continue
        if consolidate_budget is not None and consolidate_budget <= 0:
            pending.append(ep)
            budget_starved += 1
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
            if consolidate_budget is not None:
                consolidate_budget -= 1
                consolidated_this_call += 1
            continue
        from casa.domain.episode_bind import resolve_episode_concept_id

        lid = canonical_lattice_id(str(ep.get("lattice_id") or SYLLABLES_RU))
        from casa.prisms.memory.write_gate import memory_write_allowed

        allow_links = bool(
            ep.get("allow_teacher_links")
            or str(ep.get("structure_tag") or "") in ("self_promote", "canon_promote")
            or str(ep.get("correction_kind") or "") == "self_promote"
        )
        if not memory_write_allowed(state, lid, context="sleep_merge") and not allow_links:
            immutable_skipped.append(
                {
                    "episode_id": ep.get("id"),
                    "lattice_id": lid,
                    "concept_id": ep.get("concept_id"),
                    "reason": "immutable_sleep_gate",
                }
            )
            pending.append(ep)
            continue
        cid = resolve_episode_concept_id(ep, bundle, lattice_id=lid)
        if cid and not ep.get("concept_id"):
            ep = {**ep, "concept_id": cid}
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
        numeral_extract = None
        if cid and str(cid).startswith("math.num."):
            from casa.prisms.memory.f0_stack import mint_numeral_denotes_from_episode

            numeral_extract = mint_numeral_denotes_from_episode(
                lattices,
                lattice_id=lid,
                cue=str(ep.get("cue") or ""),
                concept_id=str(cid),
                copies=strength,
            )
            if numeral_extract and not extract_rep:
                extract_rep = numeral_extract
            elif numeral_extract and extract_rep:
                extract_rep = {**extract_rep, "numeral": numeral_extract}
        link_extract = None
        raw_links = ep.get("links") or []
        allow_teacher_links = bool(
            ep.get("allow_teacher_links")
            or str(ep.get("structure_tag") or "") in ("self_promote", "canon_promote")
            or str(ep.get("correction_kind") or "") == "self_promote"
        )
        if raw_links and allow_teacher_links:
            from casa.prisms.memory.f0_stack import mint_episode_links

            link_extract = mint_episode_links(
                lattices,
                lattice_id=lid,
                links=raw_links,
                copies=strength,
            )
            if link_extract and extract_rep:
                extract_rep = {**extract_rep, "links": link_extract}
            elif link_extract:
                extract_rep = {"links": link_extract}
        strengthen_context = "promote_canon" if allow_links else "sleep_merge"
        strengthened = bool(
            cid
            and _strengthen_concept(
                lattices,
                lid,
                str(cid),
                copies=strength,
                state=state,
                write_context=strengthen_context,
            )
        )
        if strengthened or link_extract:
            ep = {**ep, "consolidated": True}
            if cid:
                ep["merged_concept_id"] = cid
            item = {
                "episode_id": ep.get("id"),
                "kind": "surface",
                "lattice_id": lid,
                "concept_id": cid,
                "cue": ep.get("cue"),
                "correct": ep.get("correct"),
                "correction_kind": ep.get("correction_kind"),
                "scene": ep.get("scene"),
                "links": ep.get("links"),
            }
            if extract_rep:
                item["extract"] = extract_rep
            merged.append(item)
            if consolidate_budget is not None:
                consolidate_budget -= 1
                consolidated_this_call += 1
        else:
            pending.append(ep)

    if budget_starved > 0:
        hippo["episodes"] = pending
        persist_content_lattices(state, lattices)
        cons = state.setdefault("consolidation", {})
        cons["last_sleep_tick"] = int(state.get("field_version") or 0) + 1
        cons["episodes_merged_total"] = int(cons.get("episodes_merged_total") or 0) + len(merged)
        cons["last_sleep"] = {
            "merged": len(merged),
            "pending": len(pending),
            "z_compose": None,
            "items": merged,
            "nca": None,
            "replay": replay_report,
            "immutable_skipped": immutable_skipped,
            "batch": {
                "max_episodes": max_episodes,
                "consolidated": consolidated_this_call,
                "budget_starved": budget_starved,
                "deferred_tail": True,
            },
        }
        if store_dir is not None:
            from casa.prisms.memory.kernel_memory_health import (
                MaintainContext,
                kernel_memory_maintain_on_sleep_enabled,
                maintain_memory_kernel,
            )

            if kernel_memory_maintain_on_sleep_enabled(state):
                maintain_memory_kernel(
                    state,
                    store_dir,
                    repair=True,
                    ctx=MaintainContext(phase="sleep"),
                    report=cons["last_sleep"],
                )

        if store_dir is not None and compact_persist is not False:
            from casa.prisms.shared.compact_persist import maybe_compact_persist_after_sleep

            maybe_compact_persist_after_sleep(
                store_dir,
                state,
                cons["last_sleep"],
                force=compact_persist is True,
                skip_vocab_over=65535,
                remigrate_l2=False,
            )
        from casa.prisms.memory.forgetting import finalize_memory_sleep_reports

        finalize_memory_sleep_reports(state, cons["last_sleep"], store_dir=store_dir)
        set_active_prism(state, PRISM_MEMORY)
        state["sn"] = {**(state.get("sn") or {}), "mode": "wake"}
        state["field_version"] = int(state.get("field_version") or 0) + 1
        return cons["last_sleep"]

    from casa.prisms.memory.f0_extract_gate import (
        gate_mul_equiv_by_learning_gap,
        gate_names_by_learning_gap,
        gate_pattern_rows_by_predict_fail,
    )
    from casa.prisms.memory.f0_equiv_extract import has_equiv_cardinality_for_num
    from casa.prisms.memory.f0_names_extract import names_edges_on_field
    from casa.prisms.memory.f0_pattern_extract import count_row_group_key, numeral_surface_to_int

    def _cluster_values(rows: list[dict]) -> list[int]:
        out: list[int] = []
        for r in rows:
            v = numeral_surface_to_int(str(r.get("cue") or r.get("correct") or ""))
            if v is not None:
                out.append(v)
        return sorted(out)

    gate_pattern_rows_by_predict_fail(
        state,
        bundle,
        episodes,
        group_key_fn=count_row_group_key,
        values_fn=_cluster_values,
    )

    def _has_names_edge(cid: str) -> bool:
        prefix = f"{cid}|names|"
        return any(e.startswith(prefix) for e in names_edges_on_field(lattices, "schema-math"))

    gate_names_by_learning_gap(state, episodes, has_names_edge=_has_names_edge)

    def _has_equiv_edge(cid: str) -> bool:
        return has_equiv_cardinality_for_num(lattices, "schema-math", cid)

    gate_mul_equiv_by_learning_gap(state, episodes, has_equiv_edge=_has_equiv_edge)

    from casa.prisms.memory.f0_pattern_extract import extract_emergent_count_patterns

    from casa.prisms.memory.write_gate import memory_write_allowed as _mw_allowed

    if _mw_allowed(state, "schema-math", context="sleep_merge"):
        emergent_count = extract_emergent_count_patterns(
            lattices,
            episodes,
            state,
            lattice_id="schema-math",
            copies=strength,
        )
    else:
        emergent_count = []

    for item in emergent_count:
        if item.get("skipped"):
            merged.append(item)
            continue
        merged.append(
            {
                "episode_id": None,
                "kind": item.get("kind") or "emergent_pattern",
                "lattice_id": "schema-math",
                "concept_id": item.get("concept_id"),
                "extract": item,
            }
        )

    from casa.prisms.memory.f0_names_extract import extract_emergent_names_from_episodes

    if _mw_allowed(state, "schema-math", context="sleep_merge"):
        emergent_names = extract_emergent_names_from_episodes(
            lattices,
            episodes,
            bundle,
            state,
            lattice_id="schema-math",
            copies=strength,
        )
    else:
        emergent_names = []

    for item in emergent_names:
        merged.append(
            {
                "episode_id": item.get("episode_id"),
                "kind": "emergent_names",
                "lattice_id": "schema-math",
                "concept_id": item.get("concept_id"),
                "extract": item,
            }
        )

    from casa.prisms.memory.f0_equiv_extract import extract_emergent_mul_equiv_from_episodes

    if _mw_allowed(state, "schema-math", context="sleep_merge"):
        emergent_equiv = extract_emergent_mul_equiv_from_episodes(
            lattices,
            episodes,
            state,
            lattice_id="schema-math",
            copies=strength,
        )
    else:
        emergent_equiv = []

    for item in emergent_equiv:
        merged.append(
            {
                "episode_id": None,
                "kind": "emergent_mul_equiv",
                "lattice_id": "schema-math",
                "concept_id": item.get("concept_id"),
                "extract": item,
            }
        )

    from casa.prisms.memory.f0_successor_extract import extract_emergent_successors

    for item in extract_emergent_successors(
        lattices,
        episodes,
        state,
        lattice_id="schema-math",
        copies=strength,
    ):
        merged.append(
            {
                "episode_id": None,
                "kind": "emergent_successor",
                "lattice_id": "schema-math",
                "extract": item,
            }
        )

    from casa.prisms.visual.bridge_math import extract_emergent_vis_math_bridges
    from casa.prisms.visual.bridge_lex import extract_emergent_vis_lex_bridges

    for item in extract_emergent_vis_math_bridges(
        lattices,
        episodes,
        state,
        copies=strength,
    ):
        merged.append(
            {
                "episode_id": item.get("episode_id"),
                "kind": "emergent_crosslink",
                "lattice_id": "V1_lum",
                "concept_id": item.get("vis_concept_id"),
                "extract": item,
            }
        )

    for item in extract_emergent_vis_lex_bridges(
        lattices,
        episodes,
        state,
        copies=strength,
    ):
        merged.append(
            {
                "episode_id": item.get("episode_id"),
                "kind": "emergent_crosslink_lex",
                "lattice_id": "V1_lum",
                "extract": item,
            }
        )

    from casa.prisms.auditory.bridge_vis import extract_emergent_aud_vis_bridges
    from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM

    for item in extract_emergent_aud_vis_bridges(
        lattices,
        episodes,
        state,
        copies=strength,
    ):
        merged.append(
            {
                "episode_id": item.get("episode_id"),
                "kind": "emergent_aud_vis",
                "lattice_id": LATTICE_AUDIO_SPECTRUM,
                "concept_id": item.get("aud_concept_id"),
                "extract": item,
            }
        )

    from casa.prisms.auditory.bridge_motor import extract_emergent_motor_heard_bridges

    for item in extract_emergent_motor_heard_bridges(
        lattices,
        episodes,
        state,
        copies=strength,
    ):
        merged.append(
            {
                "episode_id": item.get("episode_id"),
                "kind": "emergent_motor_heard",
                "lattice_id": LATTICE_AUDIO_SPECTRUM,
                "concept_id": item.get("motor_concept_id"),
                "extract": item,
            }
        )

    compose = apply_z_compose(lattices, bundle, stack)

    hippo["episodes"] = pending
    persist_content_lattices(state, lattices)
    state["sss"] = {
        **(state.get("sss") or {}),
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
            persist_content_lattices(state, lattices)
            nca_report = {"mode": "regrow", "lattice_id": nca_lattice_id, **{k: v for k, v in reg.items() if k != "lattice"}}
        except Exception as exc:  # noqa: BLE001 — sleep must not fail on optional NCA
            nca_report = {"error": str(exc), "lattice_id": nca_lattice_id}

    last_sleep: dict[str, Any] = {
        "merged": len(merged),
        "pending": len(pending),
        "z_compose": compose.get("count"),
        "items": merged,
        "nca": nca_report,
        "replay": replay_report,
        "immutable_skipped": immutable_skipped,
    }
    if max_episodes is not None:
        last_sleep["batch"] = {
            "max_episodes": max_episodes,
            "consolidated": consolidated_this_call,
            "budget_starved": budget_starved,
            "deferred_tail": False,
        }
    cons["last_sleep"] = last_sleep
    if store_dir is not None:
        from casa.prisms.memory.kernel_memory_health import (
            MaintainContext,
            kernel_memory_maintain_on_sleep_enabled,
            maintain_memory_kernel,
        )

        if kernel_memory_maintain_on_sleep_enabled(state):
            maintain_memory_kernel(
                state,
                store_dir,
                repair=True,
                ctx=MaintainContext(phase="sleep"),
                report=cons["last_sleep"],
            )

        from casa.domain.boot_repair_scheduler import repair_pending, run_consistency_repair_on_sleep

        if repair_pending(state):
            cons["last_sleep"]["consistency_repair"] = run_consistency_repair_on_sleep(
                state,
                store_dir,
            )

    if store_dir is not None:
        from casa.prisms.memory.agent_canon_field import sync_agent_canon_to_field

        canon_sync = sync_agent_canon_to_field(state, store_dir)
        if canon_sync.get("synced"):
            cons["last_sleep"]["agent_canon_sync"] = canon_sync

    if store_dir is not None and compact_persist is not False:
        from casa.prisms.shared.compact_persist import maybe_compact_persist_after_sleep

        maybe_compact_persist_after_sleep(
            store_dir,
            state,
            cons["last_sleep"],
            force=compact_persist is True,
            skip_vocab_over=65535,
            remigrate_l2=False,
        )
    from casa.prisms.memory.forgetting import finalize_memory_sleep_reports

    finalize_memory_sleep_reports(state, cons["last_sleep"], store_dir=store_dir)
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
