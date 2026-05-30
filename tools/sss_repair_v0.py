#!/usr/bin/env python3
"""Cross-lattice SSS repair: compose↑, decompose↓, plasticity without claims_nav."""

from __future__ import annotations

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import copy
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from sss_stack_v0 import (  # type: ignore
    _place_token,
    apply_z_compose_v0,
    compose_sources,
    decode_lattice,
    load_stack,
)


def _has_concept(decoded: dict, cid: str) -> bool:
    return any(str(c.get("concept_id")) == cid for c in decoded.get("concepts") or [])


def _missing_concepts(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict,
    lattice_id: str,
) -> list[str]:
    lat = stack_lattice_meta(stack, lattice_id)
    prefix = str(lat.get("concept_prefix") or "")
    expected = sorted(
        {str(c["concept_id"]) for c in bundle.get("claims") or [] if str(c.get("concept_id", "")).startswith(prefix)}
    )
    dec = decode_lattice(lattices[lattice_id], min_votes=1)
    got = {str(c.get("concept_id")) for c in dec.get("concepts") or []}
    return [cid for cid in expected if cid not in got]


def stack_lattice_meta(stack: dict, lattice_id: str) -> dict:
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lattice_id:
            return lat
    raise KeyError(lattice_id)


def _place_concept(lattices: dict[str, dict], lattice_id: str, concept_id: str, *, copies: int) -> bool:
    if lattice_id not in lattices:
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


def decompose_down_v0(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict,
    *,
    copies: int = 3,
) -> list[dict[str, Any]]:
    """
    Upper lattice informs lower (inverse compose): syllable.ма on L1 → restore grapheme.м on L0.
    """
    restored: list[dict[str, Any]] = []
    lat_by_id = {str(l["id"]): l for l in stack.get("lattices") or []}

    for br in stack.get("z_bridges") or []:
        fid = str(br.get("from"))
        tid = str(br.get("to"))
        if fid not in lattices or tid not in lattices:
            continue
        to_prefix = str(lat_by_id[tid].get("concept_prefix") or "")

        dec_upper = decode_lattice(lattices[tid], min_votes=1)
        dec_lower = decode_lattice(lattices[fid], min_votes=1)

        for c in dec_upper.get("concepts") or []:
            dst = str(c.get("concept_id") or "")
            if not dst.startswith(to_prefix):
                continue
            sources = compose_sources(bundle, dst)
            if not sources:
                continue
            for src in sources:
                if _has_concept(dec_lower, src):
                    continue
                if _place_concept(lattices, fid, src, copies=copies):
                    restored.append(
                        {"via": "decompose_down", "bridge": br.get("id"), "restored": src, "from_upper": dst}
                    )
                    dec_lower = decode_lattice(lattices[fid], min_votes=1)

    return restored


def compose_up_v0(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict,
    *,
    copies: int = 3,
) -> list[dict[str, Any]]:
    """Lower → upper: missing dst when all sources present."""
    restored: list[dict[str, Any]] = []
    for br in stack.get("z_bridges") or []:
        fid = str(br.get("from"))
        tid = str(br.get("to"))
        if fid not in lattices or tid not in lattices:
            continue
        to_meta = stack_lattice_meta(stack, tid)
        prefix = str(to_meta.get("concept_prefix") or "")
        dec_lower = decode_lattice(lattices[fid], min_votes=1)
        dec_upper = decode_lattice(lattices[tid], min_votes=1)

        for c in bundle.get("claims") or []:
            dst = str(c.get("concept_id") or "")
            if not dst.startswith(prefix):
                continue
            if _has_concept(dec_upper, dst):
                continue
            sources = compose_sources(bundle, dst)
            if sources and all(_has_concept(dec_lower, s) for s in sources):
                if _place_concept(lattices, tid, dst, copies=copies):
                    restored.append({"via": "compose_up", "bridge": br.get("id"), "restored": dst, "sources": sources})
                    dec_upper = decode_lattice(lattices[tid], min_votes=1)
    return restored


def canonical_fill_v0(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict,
    *,
    lattice_id: str,
    copies: int = 3,
) -> list[str]:
    """Last resort: re-place missing concepts (canonical listen — audit path, not hot path)."""
    missing = _missing_concepts(lattices, bundle, stack, lattice_id)
    placed: list[str] = []
    for cid in missing:
        if _place_concept(lattices, lattice_id, cid, copies=copies):
            placed.append(cid)
    return placed


def repair_sss_memory(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict | None = None,
    *,
    rounds: int = 2,
    copies: int = 3,
    allow_canonical: bool = False,
) -> dict[str, Any]:
    """
    Plasticity repair loop:
    1. decompose_down — upper layer teaches lower (как «другой отдел»)
    2. compose_up — lower rebuilds upper
    3. z_compose stamp
    4. optional canonical fill for stubborn gaps
    """
    stack = stack or load_stack()
    lattices = lattices  # mutate in place
    all_steps: list[dict[str, Any]] = []

    for _ in range(max(1, rounds)):
        all_steps.extend(decompose_down_v0(lattices, bundle, stack, copies=copies))
        all_steps.extend(compose_up_v0(lattices, bundle, stack, copies=copies))

    compose = apply_z_compose_v0(lattices, bundle, stack)

    canonical: dict[str, list[str]] = {}
    if allow_canonical:
        for lat in stack.get("lattices") or []:
            lid = str(lat["id"])
            if lid in lattices:
                filled = canonical_fill_v0(lattices, bundle, stack, lattice_id=lid, copies=copies)
                if filled:
                    canonical[lid] = filled

    recovery: dict[str, dict[str, Any]] = {}
    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        if lid not in lattices:
            continue
        missing = _missing_concepts(lattices, bundle, stack, lid)
        prefix = str(lat.get("concept_prefix") or "")
        expected_n = sum(
            1 for c in bundle.get("claims") or [] if str(c.get("concept_id", "")).startswith(prefix)
        )
        got_n = expected_n - len(missing)
        recovery[lid] = {
            "expected": expected_n,
            "recovered": got_n,
            "missing": missing,
            "hit": len(missing) == 0,
        }

    return {
        "steps": len(all_steps),
        "restored_items": all_steps,
        "z_compose": compose,
        "canonical_fill": canonical,
        "recovery": recovery,
        "all_ok": all(r["hit"] for r in recovery.values() if r["expected"] > 0),
    }


def repair_field_state(state: dict, bundle: dict, stack: dict | None = None, **kwargs: Any) -> dict[str, Any]:
    from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore

    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    report = repair_sss_memory(lattices, bundle, stack, **kwargs)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["field_version"] = int(state.get("field_version") or 0) + 1
    state.setdefault("sn", {})["mode"] = "wake"
    state.setdefault("repair", {})["last_sss"] = report
    return report
