#!/usr/bin/env python3
"""Built-In concept catalog + agent-concept-graph teach on agent store (ADR-0083/0085)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice, ensure_agent_prism
from casa.prisms.memory.concept_layer import (
    CONCEPT_CORE_LATTICE,
    CONCEPT_PREFIX,
    DEFAULT_THEORY_ID,
    build_concept_honesty_report,
    canonical_concept_id,
    ensure_concept_domain,
    spawn_concept_layer,
    spawn_concept_prism,
)

CONCEPT_GRAPH_LATTICE = "agent-concept-graph"
_PROFILE_PATHS: dict[str, str] = {
    "base": "lab/curriculum/concept-net-base-v1.json",
    "wide": "lab/curriculum/concept-net-wide-v1.json",
}
_CYR_TO_LAT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _en_slug(en: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "_", str(en or "").strip().lower())
    return raw.strip("_") or "item"


def _ru_slug(ru: str) -> str:
    out: list[str] = []
    for ch in str(ru or "").strip().lower():
        if ch in _CYR_TO_LAT:
            out.append(_CYR_TO_LAT[ch])
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
        elif ch in " -":
            out.append("_")
    raw = re.sub(r"_+", "_", "".join(out))
    return raw.strip("_") or _en_slug(ru)


def hub_id_from_en(en: str) -> str:
    return f"{CONCEPT_PREFIX}{_en_slug(en)}"


def lemma_ru_id(ru: str) -> str:
    return f"lemma.ru.{_ru_slug(ru)}"


def lemma_en_id(en: str) -> str:
    return f"lemma.en.{_en_slug(en)}"


def profile_net_path(profile: str) -> Path:
    rel = _PROFILE_PATHS.get(str(profile or "base").lower())
    if not rel:
        raise ValueError(f"unknown concept profile: {profile!r}")
    path = (REPO_ROOT / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def bundle_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def ensure_concept_graph_lattice(state: dict, *, width: int = 96, height: int = 96) -> str:
    ensure_agent_prism(state)
    lats = agent_lattices(state)
    if CONCEPT_GRAPH_LATTICE not in lats:
        create_agent_lattice(
            state,
            CONCEPT_GRAPH_LATTICE,
            width=width,
            height=height,
            concept_prefix=CONCEPT_PREFIX,
        )
    return CONCEPT_GRAPH_LATTICE


def _mint_graph_edge(
    lattices: dict[str, dict],
    lattice_id: str,
    src: str,
    rel: str,
    dst: str,
    *,
    copies: int = 4,
) -> None:
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    strengthen_graph_edge(lattices, lattice_id, src, rel, dst, copies=copies)


def _graph_edges(lattices: dict[str, dict], lattice_id: str) -> list[str]:
    from casa.prisms.memory.f0_stack import decode_f0_lattice

    lat = lattices.get(lattice_id)
    return list(decode_f0_lattice(lat).get("edges") or []) if lat else []


def teach_concept_graph(
    state: dict,
    data: dict[str, Any],
    *,
    lattice_id: str | None = None,
) -> dict[str, Any]:
    """Teach isa/affords/relations + lemma name edges on agent-concept-graph."""
    lid = lattice_id or ensure_concept_graph_lattice(state)
    lats = agent_lattices(state)
    links: list[dict[str, str]] = []
    hubs: dict[str, dict[str, Any]] = {}

    for category, members in (data.get("concepts") or {}).items():
        for ru, en in members:
            ru_s, en_s = str(ru).strip(), str(en).strip()
            if not en_s:
                continue
            hub = hub_id_from_en(en_s)
            hubs[hub] = {
                "ru": (lemma_ru_id(ru_s), ru_s),
                "en": (lemma_en_id(en_s), en_s),
            }
            if ru_s:
                links.append({"src": hub, "relation": "names", "dst": lemma_ru_id(ru_s)})
            links.append({"src": hub, "relation": "names", "dst": lemma_en_id(en_s)})

    isa_pairs: list[tuple[str, str]] = []
    for cat in data.get("categories") or []:
        cat_id = str(cat.get("id") or "")
        isa_pairs += [(cat_id, sup) for sup in cat.get("isa") or []]
    for category, members in (data.get("concepts") or {}).items():
        for _ru, en in members:
            isa_pairs.append((hub_id_from_en(str(en)), str(category)))

    for sub, sup in isa_pairs:
        _mint_graph_edge(lats, lid, sub, "isa", sup)
    for cat in data.get("categories") or []:
        for role in cat.get("affords") or []:
            _mint_graph_edge(lats, lid, str(cat["id"]), "affords", str(role))
    for rel in data.get("relations") or []:
        r = str(rel.get("rel") or "")
        _mint_graph_edge(lats, lid, r, "arg1", str(rel.get("arg1") or ""))
        _mint_graph_edge(lats, lid, r, "arg2", str(rel.get("arg2") or ""))
    for whole, part in data.get("parts") or []:
        _mint_graph_edge(lats, lid, str(whole), "has_part", str(part))

    from casa.prisms.memory.f0_stack import mint_episode_links

    mint_episode_links(lats, lattice_id=lid, links=links, copies=4)

    return {
        "lattice_id": lid,
        "hubs": len(hubs),
        "isa": len(isa_pairs),
        "relations": len(data.get("relations") or []),
        "name_links": len(links),
        "hub_lex": hubs,
    }


def register_built_in_hubs(
    state: dict,
    hub_lex: dict[str, dict[str, Any]],
    *,
    theory_id: str = DEFAULT_THEORY_ID,
) -> dict[str, Any]:
    """Catalog Built-In hubs + lemma slots; index once at end."""
    registered: list[str] = []
    for hub, spec in sorted(hub_lex.items()):
        lex_pairs: dict[str, tuple[str, str]] = {}
        for loc in ("ru", "en"):
            row = spec.get(loc)
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                lex_pairs[loc] = (str(row[0]), str(row[1]))
        spawn_concept_prism(
            state,
            hub,
            theory_id=theory_id,
            provenance="bootstrap",
            lex=lex_pairs or None,
        )
        registered.append(hub)
    from casa.prisms.memory.concept_index import build_concept_hub_index

    index_rep = build_concept_hub_index(state)
    return {"registered": len(registered), "index": index_rep}


def _wire_concept_domain_shelf(state: dict, *, lattice_id: str, theory_id: str) -> None:
    dom = ensure_concept_domain(state)
    lids = set(str(x) for x in (dom.get("lattice_ids") or []))
    lids.update({CONCEPT_CORE_LATTICE, lattice_id})
    dom["lattice_ids"] = sorted(lids)
    dom["theory_id"] = theory_id
    theories = [t for t in (dom.get("theories") or []) if str(t.get("theory_id") or "") != theory_id]
    theories.append(
        {
            "theory_id": theory_id,
            "tier": "built_in",
            "active": True,
            "provenance": "operator",
        }
    )
    dom["theories"] = theories


def built_in_meta(state: dict) -> dict[str, Any]:
    meta = state.setdefault("meta", {})
    row = meta.get("concept_built_in")
    return dict(row) if isinstance(row, dict) else {}


def graph_is_populated(state: dict, lattice_id: str = CONCEPT_GRAPH_LATTICE) -> bool:
    edges = _graph_edges(agent_lattices(state), lattice_id)
    return any("|isa|" in e for e in edges)


def ensure_concept_built_in(
    state: dict,
    *,
    profile: str = "base",
    force: bool = False,
    skip_species_scaffold: bool = False,
) -> dict[str, Any]:
    """Idempotent Built-In teach: species scaffold + base/wide concept graph."""
    path = profile_net_path(profile)
    digest = bundle_hash(path)
    prior = built_in_meta(state)
    if (
        not force
        and prior.get("bundle_hash") == digest
        and prior.get("profile") == profile
        and graph_is_populated(state)
    ):
        return {
            "skipped": True,
            "profile": profile,
            "bundle_hash": digest,
            "lattice_id": CONCEPT_GRAPH_LATTICE,
            "prior": prior,
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    if not skip_species_scaffold:
        spawn_concept_layer(state, config={"theory_id": DEFAULT_THEORY_ID})

    graph_rep = teach_concept_graph(state, data)
    catalog_rep = register_built_in_hubs(state, graph_rep["hub_lex"], theory_id=DEFAULT_THEORY_ID)
    _wire_concept_domain_shelf(state, lattice_id=CONCEPT_GRAPH_LATTICE, theory_id=DEFAULT_THEORY_ID)

    dom = ensure_concept_domain(state)
    rep = {
        "skipped": False,
        "profile": profile,
        "bundle_path": str(path),
        "bundle_hash": digest,
        "lattice_id": CONCEPT_GRAPH_LATTICE,
        "theory_id": DEFAULT_THEORY_ID,
        "graph": {k: graph_rep[k] for k in ("hubs", "isa", "relations", "name_links")},
        "catalog": catalog_rep,
        "concept_count": len(dom.get("concept_ids") or []),
        "honesty": build_concept_honesty_report(state),
    }
    state.setdefault("meta", {})["concept_built_in"] = {
        "profile": profile,
        "bundle_hash": digest,
        "lattice_id": CONCEPT_GRAPH_LATTICE,
        "theory_id": DEFAULT_THEORY_ID,
        "taught_at_tick": int(state.get("field_version") or 0),
        "concept_count": rep["concept_count"],
    }
    return rep


def built_in_concept_of(state: dict, word: str, *, lattice_id: str = CONCEPT_GRAPH_LATTICE) -> str | None:
    """Resolve surface word or id to concept.* hub (store read path)."""
    raw = str(word or "").strip()
    if not raw:
        return None
    if "." in raw and " " not in raw:
        hub = canonical_concept_id(raw)
        return hub if hub.startswith(CONCEPT_PREFIX) else None

    wl = raw.lower()
    dom = ensure_concept_domain(state)
    for hub, row in (dom.get("catalog") or {}).items():
        if not str(hub).startswith(CONCEPT_PREFIX):
            continue
        for lex_row in (row.get("lex") or {}).values():
            if str(lex_row.get("surface") or "").strip().lower() == wl:
                return str(hub)

    suffix = f"|names|lang.word.{raw}"
    for edge in _graph_edges(agent_lattices(state), lattice_id):
        if edge.endswith(suffix):
            return edge.split("|names|", 1)[0].removeprefix("E:")
    return None


def built_in_validate(state: dict, rel: str, x: str, y: str, *, lattice_id: str = CONCEPT_GRAPH_LATTICE) -> dict[str, Any]:
    """Validate relation on Built-In graph (reuses curriculum affordance logic)."""
    from casa.curriculum.concept_net import validate

    cx, cy = built_in_concept_of(state, x, lattice_id=lattice_id), built_in_concept_of(state, y, lattice_id=lattice_id)
    if cx and cy:
        return validate(state, lattice_id, rel, cx, cy)
    return validate(state, lattice_id, rel, x, y)
