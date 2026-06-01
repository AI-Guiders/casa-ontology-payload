#!/usr/bin/env python3
"""Extract emergent count/sequence abstractions from hippo episode clusters (sleep)."""

from __future__ import annotations

import hashlib
import re
import secrets
from typing import Any

from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links, strengthen_graph_edge

EMERGENT_SEQUENCE_STATE_KEY = "emergent_sequence_hub"
_COUNT_ROW_SCENE = re.compile(r"count_row\s+step=(\d+)", re.I)
_COUNT_ROW_LABEL = re.compile(r"count_row(?::\s*|\s+)(.+)", re.I)
_COMMA_NUM = re.compile(r"^\s*\d+(?:\s*,\s*\d+)+\s*$")
_PATTERN_PREFIX = "math.pattern.emerged."
_STRUCT_PREFIX = "math.struct.emerged."

_NUMERAL_TO_INT: dict[str, int] = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "11": 11,
    "12": 12,
    "13": 13,
    "14": 14,
    "15": 15,
    "16": 16,
    "17": 17,
    "18": 18,
    "19": 19,
    "20": 20,
    "21": 21,
}

_INT_TO_NUMERAL_CID: dict[int, str] = {
    0: "math.num.zero",
    1: "math.num.one",
    2: "math.num.two",
    3: "math.num.three",
    4: "math.num.four",
    5: "math.num.five",
    6: "math.num.six",
    7: "math.num.seven",
    8: "math.num.eight",
    9: "math.num.nine",
    10: "math.num.ten",
    11: "math.num.eleven",
    12: "math.num.twelve",
    13: "math.num.thirteen",
    14: "math.num.fourteen",
    15: "math.num.fifteen",
    16: "math.num.sixteen",
    17: "math.num.seventeen",
    18: "math.num.eighteen",
    19: "math.num.nineteen",
    20: "math.num.twenty",
    21: "math.num.twenty_one",
}


def parse_count_row_step(scene: str) -> int | None:
    """Legacy teacher hint; prefer inferring step from episode values."""
    m = _COUNT_ROW_SCENE.search(scene or "")
    if not m:
        return None
    step = int(m.group(1))
    return step if step > 0 else None


def count_row_group_key(scene: str) -> str | None:
    """Cluster key from scene label only (no step= oracle)."""
    s = str(scene or "").strip()
    if not s:
        return None
    legacy = _COUNT_ROW_SCENE.search(s)
    if legacy:
        rest = _COUNT_ROW_SCENE.sub("", s).strip()
        return f"count_row:{rest}" if rest else None
    m = _COUNT_ROW_LABEL.match(s)
    if m:
        label = m.group(1).strip()
        if label.lower().startswith("step="):
            parts = label.split(None, 1)
            label = parts[1].strip() if len(parts) > 1 else ""
        return f"count_row:{label}" if label else None
    return None


def numeral_surface_to_int(text: str) -> int | None:
    t = str(text or "").strip()
    return _NUMERAL_TO_INT.get(t)


def numeral_int_to_concept_id(value: int) -> str | None:
    return _INT_TO_NUMERAL_CID.get(value)


def parse_comma_numeral_cue(cue: str) -> list[int] | None:
    cue = str(cue or "").strip()
    if not _COMMA_NUM.match(cue):
        return None
    parts = [p.strip() for p in cue.split(",")]
    out: list[int] = []
    for p in parts:
        v = numeral_surface_to_int(p)
        if v is None:
            return None
        out.append(v)
    return out if len(out) >= 2 else None


def constant_step(values: list[int]) -> int | None:
    if len(values) < 2:
        return None
    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    if len(set(deltas)) != 1:
        return None
    step = deltas[0]
    return step if step > 0 else None


def is_emergent_pattern_id(concept_id: str | None) -> bool:
    return bool(concept_id and str(concept_id).startswith(_PATTERN_PREFIX))


def is_emergent_struct_id(concept_id: str | None) -> bool:
    return bool(concept_id and str(concept_id).startswith(_STRUCT_PREFIX))


def _opaque_pattern_id(rows: list[dict[str, Any]], numeral_cids: list[str]) -> str:
    """Hub id from cluster identity (episode ids), not from semantic step."""
    ep_ids = sorted(str(r.get("id") or "") for r in rows if r.get("id"))
    material = "|".join(ep_ids) if ep_ids else "|".join(numeral_cids)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"{_PATTERN_PREFIX}{digest}"


def sequence_hub_id(state: dict) -> str:
    """One opaque sequence meta-hub per store lifetime (Name layer, not bundle)."""
    cons = state.setdefault("consolidation", {})
    existing = cons.get(EMERGENT_SEQUENCE_STATE_KEY)
    if existing:
        return str(existing)
    hub = f"{_STRUCT_PREFIX}{secrets.token_hex(6)}"
    cons[EMERGENT_SEQUENCE_STATE_KEY] = hub
    return hub


def index_emergent_pattern_hubs(decoded: dict) -> dict[str, dict[str, set[str]]]:
    hubs: dict[str, dict[str, set[str]]] = {}
    for edge in decoded.get("edges") or []:
        parts = str(edge).split("|")
        if len(parts) != 3:
            continue
        src, rel, dst = parts
        if not src.startswith(_PATTERN_PREFIX):
            continue
        hubs.setdefault(src, {}).setdefault(rel, set()).add(dst)
    return hubs


def match_emergent_patterns_for_values(
    decoded: dict,
    values: list[int],
    *,
    require_all_examples: bool = True,
) -> list[tuple[str, int]]:
    """Rank opaque pattern hubs whose field edges fit this numeral row."""
    step = constant_step(values)
    if step is None:
        return []
    want = {cid for v in values if (cid := numeral_int_to_concept_id(v))}
    step_cid = numeral_int_to_concept_id(step)
    if not want:
        return []
    scored: list[tuple[str, int]] = []
    for hub, rels in index_emergent_pattern_hubs(decoded).items():
        examples = rels.get("example") or set()
        if require_all_examples and not want.issubset(examples):
            continue
        if not require_all_examples and not (want & examples):
            continue
        hub_step = rels.get("step") or set()
        if step_cid and step_cid not in hub_step:
            continue
        overlap = len(want & examples)
        scored.append((hub, 28 + overlap * 8 + len(values) * 2))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def find_pattern_hub_on_field(
    lattices: dict[str, dict],
    lattice_id: str,
    *,
    numeral_cids: list[str],
    step_cid: str | None,
) -> str | None:
    if lattice_id not in lattices:
        return None
    dec = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    want = set(numeral_cids)
    for hub, rels in index_emergent_pattern_hubs(dec).items():
        examples = rels.get("example") or set()
        if not want.issubset(examples):
            continue
        if step_cid and step_cid not in (rels.get("step") or set()):
            continue
        return hub
    return None


def _cluster_count_row_episodes(
    episodes: list[dict[str, Any]],
) -> list[tuple[int, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes or []:
        if ep.get("kind") not in (None, "surface"):
            continue
        key = count_row_group_key(str(ep.get("scene") or ""))
        if not key:
            continue
        cid = ep.get("concept_id")
        if not (cid and str(cid).startswith("math.num.")):
            continue
        val = numeral_surface_to_int(str(ep.get("cue") or ep.get("correct") or ""))
        if val is None:
            continue
        groups.setdefault(key, []).append({**ep, "_value": val})
    out: list[tuple[int, list[dict[str, Any]]]] = []
    for rows in groups.values():
        rows.sort(key=lambda row: int(row["_value"]))
        values = [int(r["_value"]) for r in rows]
        step = constant_step(values)
        if step is None:
            continue
        out.append((step, rows))
    return out


def _pattern_links(
    pattern_id: str,
    sequence_id: str,
    *,
    step_cid: str | None,
    numeral_cids: list[str],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    if step_cid:
        links.append({"src": pattern_id, "relation": "step", "dst": step_cid})
    for cid in numeral_cids:
        links.append({"src": pattern_id, "relation": "example", "dst": cid})
    links.append({"src": sequence_id, "relation": "step_pattern", "dst": pattern_id})
    return links


def mint_emergent_count_pattern(
    lattices: dict[str, dict],
    state: dict,
    *,
    lattice_id: str,
    step: int,
    numeral_cids: list[str],
    rows: list[dict[str, Any]],
    copies: int = 4,
) -> dict[str, Any] | None:
    if step <= 0 or not numeral_cids or lattice_id not in lattices:
        return None
    step_cid = numeral_int_to_concept_id(step)
    existing = find_pattern_hub_on_field(
        lattices,
        lattice_id,
        numeral_cids=numeral_cids,
        step_cid=step_cid,
    )
    pattern_id = existing or _opaque_pattern_id(rows, numeral_cids)
    sequence_id = sequence_hub_id(state)
    links = _pattern_links(pattern_id, sequence_id, step_cid=step_cid, numeral_cids=numeral_cids)
    minted = mint_episode_links(lattices, lattice_id=lattice_id, links=links, copies=copies)
    strengthen_graph_edge(
        lattices,
        lattice_id,
        sequence_id,
        "kind",
        "math.struct.ordered",
        copies=max(2, copies // 2),
    )
    from casa.prisms.memory.f0_extract_gate import record_extract_provenance

    ep_ids = sorted({str(r.get("id") or "") for r in rows if r.get("id")})
    record_extract_provenance(state, pattern_id, episode_ids=ep_ids, kind="emergent_pattern")
    return {
        "kind": "emergent_pattern",
        "concept_id": pattern_id,
        "sequence_hub": sequence_id,
        "step": step,
        "examples": numeral_cids,
        "links": minted,
        "created": existing is None,
        "provenance_episodes": ep_ids,
    }


def extract_emergent_count_patterns(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    lattice_id: str = "schema-math",
    copies: int = 4,
    min_terms: int = 3,
) -> list[dict[str, Any]]:
    """Sleep Extract: surprise-gated episode clusters → opaque math.pattern.emerged.* hubs."""
    from casa.prisms.memory.f0_extract_gate import filter_form_extract_episodes

    merged: list[dict[str, Any]] = []
    groups = _cluster_count_row_episodes(filter_form_extract_episodes(episodes))
    for step, rows in sorted(groups, key=lambda pair: (pair[0], int(pair[1][0]["_value"]))):
        if len(rows) < min_terms:
            continue
        values = [int(r["_value"]) for r in rows]
        if constant_step(values) != step:
            continue
        numeral_cids = [str(r["concept_id"]) for r in rows if r.get("concept_id")]
        step_cid = numeral_int_to_concept_id(step)
        existing = find_pattern_hub_on_field(
            lattices,
            lattice_id,
            numeral_cids=numeral_cids,
            step_cid=step_cid,
        )
        if existing:
            merged.append(
                {
                    "kind": "emergent_pattern",
                    "concept_id": existing,
                    "step": step,
                    "skipped": True,
                    "reason": "already_on_field",
                }
            )
            continue
        rep = mint_emergent_count_pattern(
            lattices,
            state,
            lattice_id=lattice_id,
            step=step,
            numeral_cids=numeral_cids,
            rows=rows,
            copies=copies,
        )
        if rep:
            merged.append(rep)
    return merged


def score_emerged_patterns_from_cue(cue: str, decoded: dict) -> dict[str, int]:
    values = parse_comma_numeral_cue(cue)
    if not values:
        return {}
    scores: dict[str, int] = {}
    for hub, bonus in match_emergent_patterns_for_values(decoded, values, require_all_examples=False):
        scores[hub] = bonus
    seq_ids = {
        str(c.get("concept_id") or "")
        for c in decoded.get("concepts") or []
        if is_emergent_struct_id(str(c.get("concept_id") or ""))
    }
    if scores and seq_ids:
        for sid in seq_ids:
            scores[sid] = max(scores.values()) // 2
    return scores
