#!/usr/bin/env python3
"""Surprise / learning-gap gate for Form Extract (North Star: Extract after Critic fail)."""

from __future__ import annotations

from typing import Any

_SURPRISE_STRUCTURE = frozenset({"predict_mismatch", "self_promote", "self_verify"})
_SURPRISE_CORRECTION = frozenset({"predict_surprise", "predict_fail", "self_correct"})


def episode_surprise_gated(ep: dict[str, Any]) -> bool:
    if ep.get("form_extract_allowed"):
        return True
    if str(ep.get("structure_tag") or "") in _SURPRISE_STRUCTURE:
        return True
    if str(ep.get("correction_kind") or "") in _SURPRISE_CORRECTION:
        return True
    meta = ep.get("meta") if isinstance(ep.get("meta"), dict) else {}
    if float(meta.get("prediction_error") or 0) > 0:
        return True
    return False


def mark_episode_form_extract(state: dict, episode_id: str, *, reason: str) -> None:
    from casa.domain.prism_wire import prism_hippo

    for ep in prism_hippo(state).get("episodes") or []:
        if str(ep.get("id") or "") == episode_id:
            ep["form_extract_allowed"] = True
            ep.setdefault("extract_gate_reason", reason)
            return


def mark_episodes_form_extract(state: dict, episode_ids: list[str], *, reason: str) -> None:
    from casa.domain.prism_wire import prism_hippo

    by_id = {str(ep.get("id") or ""): ep for ep in prism_hippo(state).get("episodes") or []}
    for eid in episode_ids:
        ep = by_id.get(eid)
        if ep is not None:
            ep["form_extract_allowed"] = True
            ep.setdefault("extract_gate_reason", reason)


def mark_cluster_form_extract(rows: list[dict[str, Any]], *, reason: str) -> None:
    for ep in rows:
        ep["form_extract_allowed"] = True
        ep.setdefault("extract_gate_reason", reason)


def gate_pattern_rows_by_predict_fail(
    state: dict,
    bundle: dict,
    episodes: list[dict[str, Any]],
    *,
    group_key_fn,
    values_fn,
) -> int:
    """Comma-row predict miss → allow pattern Extract for that cluster."""
    from casa.prisms.memory.f0_pattern_extract import (
        match_emergent_patterns_for_values,
        parse_comma_numeral_cue,
    )
    from casa.prisms.memory.f0_stack import decode_f0_lattice
    from casa.prisms.memory.memory_prisms import memory_lattices
    from casa.prisms.tick.predict_tick import predict_tick

    lats = memory_lattices(state)
    lat = lats.get("schema-math")
    if not lat:
        return 0
    dec = decode_f0_lattice(lat, min_votes=1)
    groups: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes:
        key = group_key_fn(str(ep.get("scene") or ""))
        if not key:
            continue
        groups.setdefault(key, []).append(ep)

    marked = 0
    for _key, rows in groups.items():
        values = values_fn(rows)
        if len(values) < 3:
            continue
        cue = ", ".join(str(v) for v in values)
        if not parse_comma_numeral_cue(cue):
            continue
        tick = predict_tick(state, cue, modality="schema", bundle=bundle)
        hyp = (tick.get("predict") or {}).get("hypothesis")
        matches = match_emergent_patterns_for_values(dec, values)
        ok = bool(matches and hyp == matches[0][0] and tick.get("verdict") == "pass")
        if ok:
            continue
        mark_cluster_form_extract(rows, reason="pattern_row_predict_fail")
        marked += len(rows)
    return marked


def gate_mul_equiv_by_learning_gap(
    state: dict,
    episodes: list[dict[str, Any]],
    *,
    has_equiv_edge,
) -> int:
    from casa.prisms.memory.f0_equiv_extract import _cluster_rows, mul_equiv_scene_key

    groups: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes:
        key = mul_equiv_scene_key(str(ep.get("scene") or ""))
        if key:
            groups.setdefault(key, []).append(ep)

    marked = 0
    for _scene, rows in groups.items():
        parsed = _cluster_rows(rows)
        if not parsed:
            continue
        _mag, num_cid = parsed
        if has_equiv_edge(num_cid):
            continue
        mark_cluster_form_extract(rows, reason="mul_add_equiv_co_present")
        marked += len(rows)
    return marked


def gate_names_by_learning_gap(
    state: dict,
    episodes: list[dict[str, Any]],
    *,
    has_names_edge,
) -> int:
    from casa.prisms.memory.f0_names_extract import parse_bilingual_numeral_scene

    marked = 0
    for ep in episodes:
        cid = str(ep.get("concept_id") or "")
        if not cid.startswith("math.num."):
            continue
        if not parse_bilingual_numeral_scene(str(ep.get("scene") or ""))[0]:
            continue
        if has_names_edge(cid):
            continue
        eid = str(ep.get("id") or "")
        if eid:
            mark_episode_form_extract(state, eid, reason="names_co_present_gap")
            marked += 1
    return marked


def filter_form_extract_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ep for ep in episodes or [] if episode_surprise_gated(ep)]


def record_extract_provenance(state: dict, hub_id: str, *, episode_ids: list[str], kind: str) -> None:
    cons = state.setdefault("consolidation", {})
    prov = cons.setdefault("emergent_provenance", {})
    prov[hub_id] = {"kind": kind, "episode_ids": episode_ids[:24]}
