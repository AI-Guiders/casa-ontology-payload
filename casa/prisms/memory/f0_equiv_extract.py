#!/usr/bin/env python3
"""Extract add↔mul↔cardinality links from co-presented teacher scenes (sleep); score equiv cues."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from casa.prisms.memory.f0_cardinal_abstract import (
    abstract_cardinal_magnitude,
    cardinality_concept_id,
    mul_operator_on_field,
    parse_mul_cue,
)
from casa.prisms.memory.f0_extract_gate import episode_surprise_gated, record_extract_provenance
from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links

_MUL_SCENE = re.compile(r"^mul:", re.I)


def mul_equiv_scene_key(scene: str) -> str | None:
    raw = str(scene or "").strip()
    return raw if _MUL_SCENE.match(raw) else None


def parse_add_chain_magnitude(fragment: str) -> int | None:
    s = str(fragment or "").strip().replace(" ", "")
    if "+" not in s:
        return None
    if "=" in s:
        s = s.split("=", 1)[0]
    terms = re.findall(r"\d+", s)
    if len(terms) < 2:
        return None
    return sum(int(t) for t in terms)


def parse_mul_fragment(fragment: str) -> int | None:
    s = str(fragment or "").strip().replace(" ", "")
    if "*" not in s:
        return None
    if "=" in s:
        s = s.split("=", 1)[0]
    parsed = parse_mul_cue(f"{s}=?")
    if not parsed:
        return None
    step, count = parsed
    return abstract_cardinal_magnitude(step=step, count=count)


def parse_equivalence_magnitudes(cue: str) -> int | None:
    """All =-separated numeric/add/mul fragments agree → shared cardinality."""
    raw = str(cue or "").strip()
    if raw.count("=") < 1:
        return None
    parts = [p.strip() for p in re.split(r"\s*=\s*", raw)]
    mags: list[int] = []
    for part in parts:
        p = part.strip().replace(" ", "")
        if not p or p == "?":
            continue
        if p.isdigit():
            mags.append(int(p))
        elif "+" in p:
            m = parse_add_chain_magnitude(p)
            if m is not None:
                mags.append(m)
        elif "*" in p:
            m = parse_mul_fragment(p)
            if m is not None:
                mags.append(m)
    if len(mags) < 2:
        return None
    if len(set(mags)) == 1:
        return mags[0]
    return None


def parse_add_expression_magnitude(cue: str) -> int | None:
    """Add chain with optional =result, e.g. 2+2+2=6 (no mul in cue)."""
    s = str(cue or "").strip().replace(" ", "")
    if "*" in s or "+" not in s:
        return None
    if "=" in s:
        lhs, rhs = s.split("=", 1)
        rhs_clean = rhs.replace("?", "")
        lhs_mag = parse_add_chain_magnitude(lhs)
        if rhs_clean.isdigit():
            rhs_mag = int(rhs_clean)
            if lhs_mag is not None and lhs_mag != rhs_mag:
                return None
            return rhs_mag
        return lhs_mag
    return parse_add_chain_magnitude(s)


def equiv_edges_on_field(lattices: dict[str, dict], lattice_id: str) -> set[str]:
    if lattice_id not in lattices:
        return set()
    dec = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    return {e for e in dec.get("edges") or [] if "|same_cardinality|" in e}


def has_equiv_cardinality_for_num(lattices: dict[str, dict], lattice_id: str, num_cid: str) -> bool:
    prefix = f"{num_cid}|same_cardinality|"
    return any(e.startswith(prefix) for e in equiv_edges_on_field(lattices, lattice_id))


def _cluster_rows(rows: list[dict[str, Any]]) -> tuple[int, str] | None:
    cues = [str(r.get("cue") or "") for r in rows]
    if not any("+" in c for c in cues):
        return None
    if not any("*" in c for c in cues):
        return None
    corrects = {str(r.get("correct") or "").strip() for r in rows}
    corrects.discard("")
    if len(corrects) != 1:
        return None
    correct = corrects.pop()
    if not correct.isdigit():
        return None
    mag = int(correct)
    cid = cardinality_concept_id(mag)
    if not cid:
        return None
    return mag, cid


def extract_emergent_mul_equiv_from_episodes(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict | None = None,
    *,
    lattice_id: str = "schema-math",
    copies: int = 4,
) -> list[dict[str, Any]]:
    """Co-presented add-chain and mul-form in one mul: scene → same_cardinality edges."""
    if lattice_id not in lattices:
        return []
    existing = equiv_edges_on_field(lattices, lattice_id)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ep in episodes or []:
        key = mul_equiv_scene_key(str(ep.get("scene") or ""))
        if key:
            groups[key].append(ep)

    pending_links: list[dict[str, str]] = []
    reports: list[dict[str, Any]] = []
    provenance_eps: list[str] = []

    for scene, rows in groups.items():
        if not any(episode_surprise_gated(r) for r in rows):
            continue
        parsed = _cluster_rows(rows)
        if not parsed:
            continue
        mag, num_cid = parsed
        hub_id = f"math.equiv.emerged.{hashlib.sha256(scene.encode()).hexdigest()[:12]}"
        candidates = [
            {"src": num_cid, "relation": "same_cardinality", "dst": "math.op.mul"},
            {"src": num_cid, "relation": "same_cardinality", "dst": "math.op.add"},
            {"src": hub_id, "relation": "cardinality", "dst": num_cid},
            {"src": "math.op.mul", "relation": "equiv_hub", "dst": hub_id},
            {"src": "math.op.add", "relation": "equiv_hub", "dst": hub_id},
        ]
        cluster_new = False
        for link in candidates:
            edge = f"{link['src']}|{link['relation']}|{link['dst']}"
            if edge in existing:
                continue
            if link in pending_links:
                continue
            pending_links.append(link)
            existing.add(edge)
            cluster_new = True
        if not cluster_new:
            continue
        for ep in rows:
            if ep.get("id"):
                provenance_eps.append(str(ep["id"]))
        reports.append(
            {
                "kind": "emergent_mul_equiv",
                "concept_id": num_cid,
                "magnitude": mag,
                "scene": scene,
                "hub_id": hub_id,
                "episode_ids": [r.get("id") for r in rows],
            }
        )

    if pending_links:
        minted = mint_episode_links(lattices, lattice_id=lattice_id, links=pending_links, copies=copies)
        if state is not None and reports:
            record_extract_provenance(
                state,
                reports[0]["hub_id"],
                episode_ids=sorted(set(provenance_eps)),
                kind="emergent_mul_equiv",
            )
        return [{**reports[0], "links": minted, "count": len(reports), "provenance_episodes": provenance_eps}]
    return reports


def _same_cardinality_on_field(decoded: dict, num_cid: str, op_cid: str) -> bool:
    want = f"{num_cid}|same_cardinality|{op_cid}"
    return want in set(decoded.get("edges") or [])


def score_equiv_cue(cue: str, decoded: dict, bundle: dict | None = None) -> dict[str, int]:
    """Predict cardinality when add-chain and mul-form co-express one magnitude (field + parse)."""
    scores: dict[str, int] = {}
    has_mul = "*" in cue
    has_add = "+" in cue

    if has_add and has_mul and "=" in cue:
        mag_chain = parse_equivalence_magnitudes(cue)
        if mag_chain is not None and mul_operator_on_field(decoded, bundle):
            cid = cardinality_concept_id(mag_chain)
            if cid and _same_cardinality_on_field(decoded, cid, "math.op.mul"):
                scores[cid] = 64
        return scores

    if has_add and not has_mul:
        mag_add = parse_add_expression_magnitude(cue)
        if mag_add is not None:
            cid = cardinality_concept_id(mag_add)
            if cid and _same_cardinality_on_field(decoded, cid, "math.op.add"):
                scores[cid] = 56
    return scores
