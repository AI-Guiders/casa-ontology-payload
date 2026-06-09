#!/usr/bin/env python3
"""Memory write gate — immutable lattices (ADR-0068 P12g / ADR-0069 P13d)."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.zone import ensure_memory_zone, lattice_zone_tag

WRITE_CONTEXT_HOT = "hot"
WRITE_CONTEXT_SLEEP = "sleep_merge"
WRITE_CONTEXT_PROMOTE = "promote_canon"
WRITE_CONTEXT_BOOTSTRAP = "bootstrap"
WRITE_CONTEXT_OPERATOR = "operator"

_ALLOWED_WITHOUT_GATE = frozenset(
    {WRITE_CONTEXT_PROMOTE, WRITE_CONTEXT_BOOTSTRAP, WRITE_CONTEXT_OPERATOR}
)


class ImmutableLatticeWriteError(PermissionError):
    """Hot-path or sleep merge attempted to mutate an immutable lattice."""


def is_immutable_lattice(state: dict, lattice_id: str) -> bool:
    lid = str(lattice_id)
    from casa.prisms.shared.canon_lattice_policy import host_bootstrap_lattice_ids

    if lid in host_bootstrap_lattice_ids():
        return True
    tag = lattice_zone_tag(state, lid)
    if str(tag.get("mutability") or "") == "immutable":
        return True
    zone = ensure_memory_zone(state)
    imm = zone.get("immutable") or {}
    lid = str(lattice_id)
    if lid in {str(x) for x in (imm.get("lattice_ids") or [])}:
        return True
    from casa.prisms.intelligence.zone_prism_map import classify_lattice_id, load_zone_prism_map, mutability_for_lattice

    doc = load_zone_prism_map()
    classified = classify_lattice_id(lid, doc)
    return mutability_for_lattice(lid, classified, doc) == "immutable"


def memory_write_allowed(
    state: dict,
    lattice_id: str,
    *,
    context: str = WRITE_CONTEXT_HOT,
) -> bool:
    """Return False when immutable lattice must not be written in this context."""
    ctx = str(context or WRITE_CONTEXT_HOT)
    if ctx in _ALLOWED_WITHOUT_GATE:
        return True
    if ctx not in (WRITE_CONTEXT_HOT, WRITE_CONTEXT_SLEEP):
        return True
    return not is_immutable_lattice(state, lattice_id)


def assert_memory_write_allowed(
    state: dict,
    lattice_id: str,
    *,
    context: str = WRITE_CONTEXT_HOT,
) -> None:
    if memory_write_allowed(state, lattice_id, context=context):
        return
    raise ImmutableLatticeWriteError(
        f"immutable lattice {lattice_id!r} write blocked (context={context}); use promote_canon ceremony"
    )


def sync_immutable_catalog(state: dict) -> dict[str, Any]:
    """P13c — refresh memory.immutable.lattice_ids from zone index."""
    zone = ensure_memory_zone(state)
    imm = zone.setdefault("immutable", {})
    idx = (state.get("meta") or {}).get("zone_lattice_index") or {}
    from_catalog: list[str] = []
    by_domain: dict[str, list[str]] = {}
    for lid, tag in idx.items():
        if not isinstance(tag, dict):
            continue
        if str(tag.get("mutability") or "") != "immutable":
            continue
        from_catalog.append(str(lid))
        dom = str(tag.get("domain") or "_ungrouped")
        by_domain.setdefault(dom, []).append(str(lid))
    merged_ids = sorted(set(from_catalog) | {str(x) for x in (imm.get("lattice_ids") or [])})
    imm["lattice_ids"] = merged_ids
    domains = imm.setdefault("domains", {})
    for dom, lids in by_domain.items():
        block = domains.setdefault(dom, {})
        block["lattice_ids"] = sorted(set(lids) | set(block.get("lattice_ids") or []))
    return {
        "immutable_lattice_count": len(merged_ids),
        "by_domain": {k: len(v) for k, v in by_domain.items()},
        "indexed": bool(idx),
    }


def record_earned_postulate(
    state: dict,
    *,
    lattice_id: str,
    domain: str,
    theory_id: str,
    concept_ids: list[str] | None = None,
    source: str = "promote_canon",
    tick: int | None = None,
) -> dict[str, Any]:
    """P13e — append earned immutable postulate metadata (registry + memory zone)."""
    zone = ensure_memory_zone(state)
    imm = zone.setdefault("immutable", {})
    lid = str(lattice_id)
    dom = str(domain or "math")
    tid = str(theory_id)
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    theories: list[dict[str, Any]] = list(imm.get("theories") or [])
    row = next((t for t in theories if t.get("theory_id") == tid), None)
    if row is None:
        row = {
            "theory_id": tid,
            "domain": dom,
            "active": True,
            "provenance": "earned",
            "lattice_ids": [],
            "concept_ids": [],
            "earned_at_tick": fv,
            "source": source,
        }
        theories.append(row)
    for other in theories:
        if other is not row and other.get("domain") == dom:
            other["active"] = False
    row["active"] = True
    row["domain"] = dom
    lids = set(str(x) for x in (row.get("lattice_ids") or []))
    lids.add(lid)
    row["lattice_ids"] = sorted(lids)
    if concept_ids:
        cids = set(str(x) for x in (row.get("concept_ids") or []))
        cids.update(str(c) for c in concept_ids if c)
        row["concept_ids"] = sorted(cids)
    row["updated_at_tick"] = fv
    imm["theories"] = theories
    catalog = set(str(x) for x in (imm.get("lattice_ids") or []))
    catalog.add(lid)
    imm["lattice_ids"] = sorted(catalog)
    meta = state.setdefault("meta", {})
    meta["active_theory_id"] = tid
    meta["active_theory_domain"] = dom
    return {"theory_id": tid, "domain": dom, "lattice_id": lid, "active": True}


def active_theory_for_domain(state: dict, domain: str = "") -> dict[str, Any] | None:
    zone = ensure_memory_zone(state)
    theories = (zone.get("immutable") or {}).get("theories") or []
    dom = str(domain or "").strip()
    for row in theories:
        if not isinstance(row, dict) or not row.get("active"):
            continue
        if dom and str(row.get("domain") or "") != dom:
            continue
        return dict(row)
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    tid = meta.get("active_theory_id")
    if tid:
        return {
            "theory_id": str(tid),
            "domain": str(meta.get("active_theory_domain") or dom or ""),
            "active": True,
        }
    return None
