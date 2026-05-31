#!/usr/bin/env python3
"""Act-phase NCA rollout on memory lattice (UC Use hot path)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.memory.lexicon_shard import nca_model_registry
from casa.prisms.memory.memory_prisms import memory_lattices, prism_memory
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.shared.store_layout import repo_root, resolve_nca_lattice_dir
from casa.prisms.shared.store_persist import mark_runtime_dirty


def active_memory_lattice_id(state: dict, lattice_id: str | None = None) -> str:
    from casa.prisms.memory.memory_prisms import memory_lattices

    lattices = memory_lattices(state)
    if lattice_id and lattice_id in lattices:
        return lattice_id

    sn = state.get("sn") or {}
    mem = (state.get("prisms") or {}).get("prism_memory") or {}
    sss = state.get("sss") or {}
    for cand in (
        mem.get("active_lattice"),
        sn.get("active_lattice"),
        sss.get("active_lattice"),
        lattice_id,
        "L0_grapheme",
    ):
        if cand and str(cand) in lattices:
            return str(cand)
    if lattices:
        return next(iter(lattices))
    return str(lattice_id or mem.get("active_lattice") or "L0_grapheme")


def resolve_nca_model_path(store_dir: Path, state: dict, lattice_id: str) -> Path | None:
    """Resolve NCA checkpoint for a lattice (registry → store nca/ → global model_path)."""
    store_dir = store_dir.resolve()
    raw = nca_model_registry(state).get(lattice_id)
    candidates: list[Path] = []
    if raw:
        p = Path(str(raw))
        if p.is_file():
            candidates.append(p.resolve())
        else:
            for base in (repo_root(), store_dir):
                cand = (base / raw).resolve()
                if cand.is_file():
                    candidates.append(cand)
    nca_dir = resolve_nca_lattice_dir(store_dir, lattice_id)
    for name in ("model.pt", "best.pt", "checkpoint.pt", "weights.pt"):
        cand = nca_dir / name
        if cand.is_file():
            candidates.append(cand.resolve())
    global_raw = (state.get("nca") or {}).get("model_path")
    if global_raw:
        gp = Path(str(global_raw))
        if gp.is_file():
            candidates.append(gp.resolve())
        else:
            for base in (repo_root(), store_dir):
                cand = (base / global_raw).resolve()
                if cand.is_file():
                    candidates.append(cand)
    return candidates[0] if candidates else None


def merge_decoded_digests(base: dict, extra: dict | None) -> dict:
    """Union field decode with memory-lattice decode (max votes per concept)."""
    if not extra:
        return dict(base)
    out = dict(base)
    vote: dict[str, int] = {}
    for c in out.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid:
            vote[cid] = int(c.get("votes") or 0)
    for c in extra.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if not cid:
            continue
        vote[cid] = max(vote.get(cid, 0), int(c.get("votes") or 0))
    edges = sorted(set(list(out.get("edges") or []) + list(extra.get("edges") or [])))
    concepts = [{"concept_id": cid, "votes": v} for cid, v in vote.items()]
    concepts.sort(key=lambda c: (-int(c["votes"]), c["concept_id"]))
    out["concept_ids"] = [c["concept_id"] for c in concepts]
    out["concepts"] = concepts
    out["edges"] = edges
    out["memory_merged"] = True
    return out


def act_rollout_phase(
    state: dict,
    store_dir: Path,
    *,
    lattice_id: str | None = None,
    device: str = "cpu",
) -> dict[str, Any]:
    """Run NCA k-step rollout on active memory lattice; update state in place."""
    lid = active_memory_lattice_id(state, lattice_id)
    lattices = memory_lattices(state)
    if lid not in lattices:
        return {"skipped": True, "reason": "no_lattice", "lattice_id": lid}

    base_decoded = decode_lattice(lattices[lid], min_votes=1)
    model_path = resolve_nca_model_path(store_dir, state, lid)
    if model_path is None:
        return {
            "skipped": True,
            "reason": "no_nca_model",
            "lattice_id": lid,
            "decoded": base_decoded,
        }

    try:
        from casa.prisms.memory.nca_repair import nca_regrow_lattice

        reg = nca_regrow_lattice(lattices[lid], model_path, device=device)
        lattices[lid] = reg["lattice"]
        prism_memory(state)["lattices"] = lattices
        state.setdefault("sss", {})["lattices"] = lattices
        decoded = decode_lattice(lattices[lid], min_votes=1)
        state.setdefault("nca", {})["last_act_rollout"] = {
            "lattice_id": lid,
            "model": str(model_path),
            "w_before": reg.get("w_before"),
            "w_after": reg.get("w_after"),
        }
        mark_runtime_dirty(state)
        return {
            "skipped": False,
            "lattice_id": lid,
            "model": str(model_path),
            "w_before": reg.get("w_before"),
            "w_after": reg.get("w_after"),
            "decoded": decoded,
        }
    except Exception as exc:  # noqa: BLE001 — act path must not abort tick
        return {
            "skipped": True,
            "reason": "error",
            "error": str(exc),
            "lattice_id": lid,
            "decoded": base_decoded,
        }
