#!/usr/bin/env python3
"""Concept layer — concept.* hub vs lex.{locale}.* surfaces (ADR-0073 P18)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id

CONCEPT_PREFIX = "concept."
LEX_RU_PREFIX = "lex.ru."
LEX_EN_PREFIX = "lex.en."
CONCEPT_CORE_LATTICE = "agent-concept-core"
CONCEPT_HONESTY_JSON = "concept_honesty_report.json"
DEFAULT_THEORY_ID = "species-concept-bootstrap-v1"

# Species scaffold @ T=0 — hub + lex surfaces + legacy read aliases (P18c).
SPECIES_CONCEPT_BOOTSTRAP: dict[str, dict[str, Any]] = {
    "concept.orange": {
        "lex": {
            "ru": ("lex.ru.apelsin", "апельсин"),
            "en": ("lex.en.orange", "orange"),
        },
        "legacy_concept_ids": ["lang.word.apelsin", "lang.word.apelsin_cap"],
    },
    "concept.window": {
        "lex": {
            "ru": ("lex.ru.okno", "окно"),
            "en": ("lex.en.window", "window"),
        },
        "legacy_concept_ids": ["lang.word.okno"],
    },
    "concept.door": {
        "lex": {
            "ru": ("lex.ru.dver", "дверь"),
            "en": ("lex.en.door", "door"),
        },
        "legacy_concept_ids": ["lang.word.dver", "lang.word.dverь"],
    },
    "concept.agent.self": {
        "lex": {"ru": ("lex.ru.self", "я"), "en": ("lex.en.self", "I")},
        "legacy_concept_ids": ["ru.dialog.self"],
        "discourse": {"ru": "discourse.ru.self", "en": "discourse.en.self"},
    },
}

DISCOURSE_READ_ALIASES: dict[str, str] = {
    "ru.dialog.greeting": "discourse.ru.greeting",
    "ru.dialog.thanks": "discourse.ru.thanks",
    "ru.dialog.farewell": "discourse.ru.farewell",
    "ru.dialog.how_are_you": "discourse.ru.how_are_you",
    "ru.dialog.self": "discourse.ru.self",
    "ru.dialog.affect": "discourse.ru.affect",
    "ru.dialog.capabilities": "discourse.ru.capabilities",
    "ru.dialog.explain": "discourse.ru.explain",
}


def _slugify(surface: str) -> str:
    raw = re.sub(r"[^a-z0-9\u0400-\u04FF]+", "_", str(surface or "").strip().lower())
    return raw.strip("_") or "item"


def legacy_to_concept_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for hub, spec in SPECIES_CONCEPT_BOOTSTRAP.items():
        for legacy in spec.get("legacy_concept_ids") or []:
            out[str(legacy)] = hub
        for loc, pair in (spec.get("lex") or {}).items():
            if isinstance(pair, (list, tuple)) and pair:
                out[str(pair[0])] = hub
    return out


def canonical_discourse_id(concept_id: str) -> str:
    cid = str(concept_id or "").strip()
    if cid.startswith("discourse."):
        return cid
    return DISCOURSE_READ_ALIASES.get(cid, cid)


def canonical_concept_id(concept_id: str) -> str:
    """Resolve legacy/lang.word/lex.* → concept.* hub when mapped (P18b)."""
    cid = canonical_lex_concept_id(str(concept_id or "").strip())
    if not cid:
        return cid
    if cid.startswith(CONCEPT_PREFIX):
        return cid
    if cid.startswith("lang.meta."):
        return cid
    mapped = legacy_to_concept_map().get(cid)
    if mapped:
        return mapped
    if cid.startswith("lang.word."):
        surface = cid.removeprefix("lang.word.")
        for hub, spec in SPECIES_CONCEPT_BOOTSTRAP.items():
            for loc, pair in (spec.get("lex") or {}).items():
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                if _slugify(str(pair[1])) == _slugify(surface) or str(pair[1]).lower() == surface.lower():
                    return hub
    return cid


def bind_concept_id(concept_id: str) -> str:
    """Bind budget hub — concept.* for lex/discourse/legacy surfaces (P18d)."""
    cid = canonical_concept_id(concept_id)
    if cid.startswith(("ru.dialog.", "ru.prop.", "ru.grammar.")):
        disc = canonical_discourse_id(cid)
        hub = legacy_to_concept_map().get(cid) or legacy_to_concept_map().get(disc)
        if hub:
            return hub
    return cid


def discourse_concept_id(block: dict[str, Any]) -> str:
    """Partner discourse slot id — surface ru.dialog.* even when bind hub is concept.*."""
    surface = str(block.get("surface_concept_id") or "").strip()
    if surface.startswith("ru.dialog."):
        return surface
    cid = str(block.get("concept_id") or block.get("bind_hub") or "").strip()
    if cid.startswith("ru.dialog."):
        return cid
    if cid.startswith(CONCEPT_PREFIX):
        spec = SPECIES_CONCEPT_BOOTSTRAP.get(cid) or {}
        for legacy in spec.get("legacy_concept_ids") or []:
            leg = str(legacy)
            if leg.startswith("ru.dialog."):
                return leg
    return cid


def is_concept_hub(concept_id: str) -> bool:
    return str(concept_id or "").startswith(CONCEPT_PREFIX)


def is_lexeme(concept_id: str) -> bool:
    cid = str(concept_id or "")
    return cid.startswith((LEX_RU_PREFIX, LEX_EN_PREFIX))


def lex_for_locale(concept_id: str, locale: str = "ru") -> str | None:
    hub = canonical_concept_id(concept_id)
    if not hub.startswith(CONCEPT_PREFIX):
        return None
    spec = SPECIES_CONCEPT_BOOTSTRAP.get(hub) or {}
    pair = (spec.get("lex") or {}).get(str(locale or "ru").lower())
    if isinstance(pair, (list, tuple)) and pair:
        return str(pair[0])
    return None


def lex_surface_for_locale(concept_id: str, locale: str = "ru") -> str | None:
    hub = canonical_concept_id(concept_id)
    spec = SPECIES_CONCEPT_BOOTSTRAP.get(hub) or {}
    pair = (spec.get("lex") or {}).get(str(locale or "ru").lower())
    if isinstance(pair, (list, tuple)) and len(pair) > 1:
        return str(pair[1])
    return None


def ensure_concept_domain(state: dict) -> dict[str, Any]:
    """Wire memory.immutable.domains.concept (P18a)."""
    from casa.prisms.memory.zone import ensure_memory_zone

    zone = ensure_memory_zone(state)
    imm = zone.setdefault("immutable", {})
    domains = imm.setdefault("domains", {})
    concept_dom = domains.setdefault(
        "concept",
        {
            "theory_id": DEFAULT_THEORY_ID,
            "provenance": "bootstrap",
            "concept_ids": [],
            "lattice_ids": [],
            "spawn_policy": {
                "hot_write": False,
                "promote": "genetic.promote_canon",
                "fork": "theory_branch",
            },
        },
    )
    return concept_dom


def spawn_concept_prism(
    state: dict,
    concept_id: str,
    *,
    theory_id: str = "",
    provenance: str = "bootstrap",
    tick: int | None = None,
) -> dict[str, Any]:
    """Catalog one concept hub under immutable.domains.concept (P18g)."""
    from casa.prisms.memory.agent_prism import ensure_agent_prism

    hub = canonical_concept_id(concept_id)
    if not hub.startswith(CONCEPT_PREFIX):
        raise ValueError(f"not a concept hub id: {concept_id!r}")
    dom = ensure_concept_domain(state)
    cids = sorted(set(str(x) for x in (dom.get("concept_ids") or [])) | {hub})
    dom["concept_ids"] = cids
    lids = set(str(x) for x in (dom.get("lattice_ids") or []))
    lids.add(CONCEPT_CORE_LATTICE)
    dom["lattice_ids"] = sorted(lids)
    if theory_id:
        dom["theory_id"] = str(theory_id)
    dom["provenance"] = str(provenance)
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    dom["updated_at_tick"] = fv
    catalog = dom.setdefault("catalog", {})
    slug = hub.removeprefix(CONCEPT_PREFIX)
    catalog[hub] = {
        "concept_id": hub,
        "slug": slug,
        "lex": {
            loc: {"concept_id": pair[0], "surface": pair[1]}
            for loc, pair in (SPECIES_CONCEPT_BOOTSTRAP.get(hub, {}).get("lex") or {}).items()
            if isinstance(pair, (list, tuple)) and len(pair) >= 2
        },
        "legacy_concept_ids": list(SPECIES_CONCEPT_BOOTSTRAP.get(hub, {}).get("legacy_concept_ids") or []),
        "provenance": provenance,
        "indexed_at_tick": fv,
    }
    block = ensure_agent_prism(state)
    lats = block.setdefault("lattices", {})
    if CONCEPT_CORE_LATTICE not in lats:
        from casa.prisms.memory.agent_prism import create_agent_lattice

        create_agent_lattice(
            state,
            CONCEPT_CORE_LATTICE,
            width=32,
            height=32,
            concept_prefix=CONCEPT_PREFIX,
        )
    from casa.prisms.memory.concept_index import index_concept_hub

    index_rep = index_concept_hub(state, hub, tick=fv)
    return {
        "concept_id": hub,
        "lattice_id": CONCEPT_CORE_LATTICE,
        "catalog_size": len(catalog),
        "index": index_rep,
    }


def spawn_concept_layer(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bootstrap species concept scaffold into Concept Zone (P18a-c)."""
    cfg = config or {}
    theory = str(cfg.get("theory_id") or DEFAULT_THEORY_ID)
    spawned: list[str] = []
    for hub in sorted(SPECIES_CONCEPT_BOOTSTRAP.keys()):
        if cfg.get("concept_ids") and hub not in cfg["concept_ids"]:
            continue
        spawn_concept_prism(state, hub, theory_id=theory, provenance="bootstrap")
        spawned.append(hub)
    dom = ensure_concept_domain(state)
    dom["theory_id"] = theory
    dom["bootstrap_count"] = len(spawned)
    from casa.prisms.memory.concept_index import build_concept_hub_index

    index_rep = build_concept_hub_index(state)
    return {
        "theory_id": theory,
        "concept_ids": spawned,
        "lattice_id": CONCEPT_CORE_LATTICE,
        "index": index_rep,
    }


def normalize_bind_block(row: dict[str, Any]) -> dict[str, Any]:
    """Attach bind hub + preserve surface provenance (P18d)."""
    out = dict(row)
    raw = str(out.get("concept_id") or "")
    if not raw:
        return out
    hub = bind_concept_id(raw)
    if hub != raw:
        out.setdefault("surface_concept_id", raw)
        out["concept_id"] = hub
    out["bind_hub"] = hub
    return out


def normalize_bind_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_hubs: set[str] = set()
    for row in blocks:
        norm = normalize_bind_block(row)
        hub = str(norm.get("bind_hub") or norm.get("concept_id") or "")
        if hub and hub in seen_hubs:
            continue
        if hub:
            seen_hubs.add(hub)
        deduped.append(norm)
    return deduped


def concept_layer_snapshot(state: dict) -> dict[str, Any]:
    dom = ensure_concept_domain(state)
    return {
        "theory_id": dom.get("theory_id"),
        "concept_count": len(dom.get("concept_ids") or []),
        "concept_ids": list(dom.get("concept_ids") or []),
        "lattice_ids": list(dom.get("lattice_ids") or []),
        "catalog_keys": sorted((dom.get("catalog") or {}).keys()),
    }


def probe_cross_surface_activation() -> dict[str, Any]:
    """RU lex, EN lex, legacy lang.word → same concept hub (P18f)."""
    cases = [
        ("lex.ru.apelsin", "concept.orange"),
        ("lex.en.orange", "concept.orange"),
        ("lang.word.apelsin", "concept.orange"),
        ("lex.ru.okno", "concept.window"),
        ("lex.en.window", "concept.window"),
        ("ru.dialog.self", "concept.agent.self"),
    ]
    results = [
        {"input": raw, "expected": exp, "hub": bind_concept_id(raw), "pass": bind_concept_id(raw) == exp}
        for raw, exp in cases
    ]
    return {"pass": all(r["pass"] for r in results), "cases": results}


def probe_locale_router() -> dict[str, Any]:
    """EN/RU lex surfaces route to the same hub (P18f)."""
    pairs = [
        ("concept.window", "ru", "concept.window"),
        ("concept.window", "en", "concept.window"),
        ("lang.word.okno", "ru", "concept.window"),
        ("lex.en.window", "en", "concept.window"),
    ]
    results = []
    for cid, loc, expected in pairs:
        hub = bind_concept_id(cid)
        results.append(
            {
                "concept_id": cid,
                "locale": loc,
                "hub": hub,
                "lex_id": lex_for_locale(hub, loc),
                "pass": hub == expected,
            }
        )
    return {"pass": all(r["pass"] for r in results), "cases": results}


def probe_catalog_coverage(state: dict) -> dict[str, Any]:
    dom = ensure_concept_domain(state)
    bootstrapped = set(SPECIES_CONCEPT_BOOTSTRAP.keys())
    wired = set(dom.get("concept_ids") or [])
    missing = sorted(bootstrapped - wired)
    return {
        "pass": not missing,
        "bootstrap_count": len(bootstrapped),
        "wired_count": len(wired),
        "missing": missing,
    }


def build_concept_honesty_report(state: dict) -> dict[str, Any]:
    probes = {
        "cross_surface": probe_cross_surface_activation(),
        "locale_router": probe_locale_router(),
        "catalog_coverage": probe_catalog_coverage(state),
    }
    report = {
        "schema_version": 1,
        "snapshot": concept_layer_snapshot(state),
        "probes": probes,
        "gate_pass": all(bool(p.get("pass")) for p in probes.values()),
    }
    meta = state.setdefault("meta", {})
    meta["concept_honesty_last"] = report
    return report


def write_concept_honesty_artifact(store_dir, report: dict[str, Any]) -> Path:
    path = Path(store_dir) / CONCEPT_HONESTY_JSON
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
