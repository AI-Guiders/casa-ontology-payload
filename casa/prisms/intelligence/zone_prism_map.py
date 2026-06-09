#!/usr/bin/env python3
"""Zone → prism → lattice classification (ADR-0067 / ADR-0068)."""

from __future__ import annotations

import fnmatch
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT

DEFAULT_MAP_PATH = REPO_ROOT / "design" / "zone-prism-map.v1.json"
ZONE_PRISM_MAP_VERSION = 2


@dataclass
class LatticeTag:
    lattice_id: str
    owner_zone: str
    owning_prism_id: str = ""
    memory_kind: str = ""
    memory_subkind: str = ""
    domain: str = ""
    client_zones: list[str] = field(default_factory=list)
    intelligence_zone: str = ""
    mutability: str = ""
    source: str = "field"

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v != "" and v != []}


def _mutability_rules(doc: dict[str, Any]) -> dict[str, Any]:
    mem = doc.get("memory_zone") or {}
    rules = mem.get("mutability") or {}
    return {
        "immutable_patterns": list(rules.get("immutable_lattice_patterns") or []),
        "immutable_ids": {str(x) for x in (rules.get("immutable_lattice_ids") or [])},
        "default_episodic": str(rules.get("default_episodic") or "mutable"),
        "default_implicit": str(rules.get("default_implicit") or "mutable"),
    }


def mutability_for_lattice(lattice_id: str, tag: LatticeTag, doc: dict[str, Any]) -> str:
    """immutable | mutable — ADR-0068 §3."""
    rules = _mutability_rules(doc)
    lid = str(lattice_id)
    if lid in rules["immutable_ids"] or _patterns_match(lid, rules["immutable_patterns"]):
        return "immutable"
    if tag.memory_kind == "implicit" or tag.memory_subkind == "episodic":
        return rules["default_episodic"] if tag.memory_subkind == "episodic" else rules["default_implicit"]
    if tag.owner_zone == "memory" and tag.memory_subkind == "semantic":
        return "mutable"
    if lid.startswith("agent-"):
        return "mutable"
    return "mutable"


def load_zone_prism_map(path: Path | None = None) -> dict[str, Any]:
    map_path = (path or DEFAULT_MAP_PATH).resolve()
    doc = json.loads(map_path.read_text(encoding="utf-8"))
    if int(doc.get("schema_version") or 0) < 2:
        raise ValueError(f"zone-prism-map schema_version >= 2 required: {map_path}")
    return doc


def _patterns_match(lattice_id: str, patterns: list[str]) -> bool:
    lid = str(lattice_id)
    for raw in patterns:
        pat = str(raw)
        if pat == lid:
            return True
        if fnmatch.fnmatch(lid, pat):
            return True
        if "*" not in pat and pat.endswith("*") is False:
            if lid.startswith(pat):
                return True
    return False


def _ids_match(lattice_id: str, ids: list[str]) -> bool:
    return str(lattice_id) in {str(x) for x in ids}


def _first_intelligence_agent_zone(doc: dict[str, Any], lattice_id: str) -> tuple[str, str]:
    zones = doc.get("intelligence_zones") or {}
    for zone_id, cfg in zones.items():
        if not isinstance(cfg, dict):
            continue
        patterns = list(cfg.get("agent_lattice_patterns") or [])
        if patterns and _patterns_match(lattice_id, patterns):
            return zone_id, str(cfg.get("role") or "")
    return "", ""


def _infer_owning_prism(lattice_id: str, tag: LatticeTag, doc: dict[str, Any]) -> str:
    lid = str(lattice_id)
    mem = doc.get("memory_zone") or {}
    if tag.memory_subkind == "episodic":
        return "prism_hippo"
    if tag.domain or tag.memory_subkind == "semantic":
        if lid.startswith("agent-wm-"):
            return "wm_prism"
        return "prism_memory"
    exec_cfg = (doc.get("intelligence_zones") or {}).get("executive") or {}
    if _patterns_match(lid, list(exec_cfg.get("lattice_patterns") or [])):
        return "prism_control"
    if lid.startswith("agent-"):
        return "prism_agent"
    return ""


def classify_lattice_id(lattice_id: str, doc: dict[str, Any], *, source: str = "field") -> LatticeTag:
    """Assign owner_zone + memory domain from zone-prism-map v2."""
    lid = str(lattice_id)
    mem = doc.get("memory_zone") or {}
    mem_zone_id = str(mem.get("zone_id") or "memory")
    explicit = mem.get("explicit") or {}

    episodic = explicit.get("episodic") or {}
    if _patterns_match(lid, list(episodic.get("lattice_patterns") or [])):
        return LatticeTag(
            lattice_id=lid,
            owner_zone=mem_zone_id,
            owning_prism_id="prism_hippo",
            memory_kind="explicit",
            memory_subkind="episodic",
            source=source,
        )

    semantic = explicit.get("semantic") or {}
    domains = semantic.get("domains") or {}
    for domain_id, dom_cfg in domains.items():
        if not isinstance(dom_cfg, dict):
            continue
        if _ids_match(lid, list(dom_cfg.get("lattice_ids") or [])):
            return LatticeTag(
                lattice_id=lid,
                owner_zone=mem_zone_id,
                owning_prism_id="prism_memory",
                memory_kind="explicit",
                memory_subkind="semantic",
                domain=str(domain_id),
                client_zones=[str(z) for z in (dom_cfg.get("client_zones") or [])],
                source=source,
            )
        if _patterns_match(lid, list(dom_cfg.get("lattice_patterns") or [])):
            return LatticeTag(
                lattice_id=lid,
                owner_zone=mem_zone_id,
                owning_prism_id="prism_memory",
                memory_kind="explicit",
                memory_subkind="semantic",
                domain=str(domain_id),
                client_zones=[str(z) for z in (dom_cfg.get("client_zones") or [])],
                source=source,
            )

    wm_patterns = list(semantic.get("agent_lattice_patterns") or [])
    if _patterns_match(lid, wm_patterns):
        return LatticeTag(
            lattice_id=lid,
            owner_zone=mem_zone_id,
            owning_prism_id="wm_prism",
            memory_kind="explicit",
            memory_subkind="semantic",
            domain="lang",
            client_zones=["linguistic"],
            intelligence_zone="linguistic",
            source=source,
        )

    zones = doc.get("intelligence_zones") or {}
    for zone_id, cfg in zones.items():
        if zone_id == "executive" or not isinstance(cfg, dict):
            continue
        lat_patterns = list(cfg.get("lattice_patterns") or [])
        if lat_patterns and _patterns_match(lid, lat_patterns):
            return LatticeTag(
                lattice_id=lid,
                owner_zone=str(zone_id),
                owning_prism_id="prism_control" if zone_id == "perceptual" else "",
                intelligence_zone=str(zone_id),
                source=source,
            )

    exec_cfg = zones.get("executive") or {}
    if _patterns_match(lid, list(exec_cfg.get("lattice_patterns") or [])):
        return LatticeTag(
            lattice_id=lid,
            owner_zone="executive",
            owning_prism_id="prism_control",
            intelligence_zone="executive",
            source=source,
        )
    if _patterns_match(lid, list(exec_cfg.get("agent_lattice_patterns") or [])):
        return LatticeTag(
            lattice_id=lid,
            owner_zone="executive",
            owning_prism_id="prism_agent",
            intelligence_zone="executive",
            source=source,
        )

    intel_zone, _role = _first_intelligence_agent_zone(doc, lid)
    if intel_zone:
        return LatticeTag(
            lattice_id=lid,
            owner_zone=intel_zone,
            owning_prism_id="prism_agent",
            intelligence_zone=intel_zone,
            source=source,
        )

    if lid.startswith("agent-"):
        return LatticeTag(
            lattice_id=lid,
            owner_zone="unknown",
            owning_prism_id="prism_agent",
            source=source,
        )

    return LatticeTag(lattice_id=lid, owner_zone="unknown", source=source)


def discover_store_lattice_ids(store_dir: Path, state: dict) -> dict[str, str]:
    """Return lattice_id → source label."""
    from casa.prisms.memory.agent_prism import agent_lattices, load_agent_prism
    from casa.prisms.memory.memory_prisms import memory_lattices
    from casa.prisms.shared.migrate_lattice_ids_v1 import discover_lattice_ids
    from casa.domain.prism_wire import prism_control, prism_hippo

    load_agent_prism(store_dir, state)
    found: dict[str, str] = {}
    for lid in discover_lattice_ids(store_dir):
        found[str(lid)] = "ltm/field/nca"
    for lid in memory_lattices(state):
        found[str(lid)] = "prism_memory"
    for lid in (prism_control(state).get("lattices") or {}):
        found[str(lid)] = "prism_control"
    for lid in (prism_hippo(state).get("lattices") or {}):
        found[str(lid)] = "prism_hippo"
    for lid in agent_lattices(state):
        found[str(lid)] = "prism_agent"
    return found


def build_lattice_index(
    store_dir: Path,
    state: dict,
    doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify all lattices; return report dict (dry-run safe)."""
    map_doc = doc or load_zone_prism_map()
    ids = discover_store_lattice_ids(store_dir, state)
    tags: list[LatticeTag] = []
    for lid, src in sorted(ids.items()):
        tag = classify_lattice_id(lid, map_doc, source=src)
        if not tag.owning_prism_id:
            tag.owning_prism_id = _infer_owning_prism(lid, tag, map_doc)
        tag.mutability = mutability_for_lattice(lid, tag, map_doc)
        tags.append(tag)

    by_owner: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    by_mutability: dict[str, int] = {}
    unknown: list[str] = []
    for tag in tags:
        by_owner[tag.owner_zone] = by_owner.get(tag.owner_zone, 0) + 1
        if tag.domain:
            by_domain[tag.domain] = by_domain.get(tag.domain, 0) + 1
        if tag.mutability:
            by_mutability[tag.mutability] = by_mutability.get(tag.mutability, 0) + 1
        if tag.owner_zone == "unknown":
            unknown.append(tag.lattice_id)

    return {
        "schema_version": ZONE_PRISM_MAP_VERSION,
        "store": store_dir.name,
        "lattice_count": len(tags),
        "by_owner_zone": dict(sorted(by_owner.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "by_mutability": dict(sorted(by_mutability.items())),
        "unknown_lattice_ids": unknown,
        "entries": [t.to_dict() for t in tags],
    }


def memory_resolve_scopes(
    doc: dict[str, Any],
    *,
    tract: str,
    client_zone: str = "",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shadow routing: tract + optional client → allowed domains and memory kinds (P11b/P12h)."""
    tract = str(tract or "general").strip().lower()
    zones = doc.get("intelligence_zones") or {}
    client = client_zone or _default_client_for_tract(tract, zones)
    cfg = zones.get(client) or {}
    access = cfg.get("memory_access") or {}
    explicit = access.get("explicit") or {}
    domains = [str(d) for d in (explicit.get("semantic_domains") or [])]
    if explicit.get("episodic"):
        episodic = True
    else:
        episodic = tract == "recall" or client == "executive"
    scope: dict[str, Any] = {
        "tract": tract,
        "client_zone": client,
        "semantic_domains": domains,
        "explicit_episodic": episodic,
        "implicit_procedural": bool((access.get("implicit") or {}).get("procedural")),
    }
    if state is None:
        return scope
    primary_domain = domains[0] if domains else ("math" if tract == "math" else "lang")
    from casa.prisms.memory.write_gate import active_theory_for_domain
    from casa.prisms.memory.zone import ensure_memory_zone

    theory = active_theory_for_domain(state, primary_domain)
    if theory:
        scope["active_theory_id"] = str(theory.get("theory_id") or "")
        scope["active_theory_domain"] = str(theory.get("domain") or primary_domain)
        scope["active_theory_lattice_ids"] = [
            str(x) for x in (theory.get("lattice_ids") or []) if x
        ]
    zone = ensure_memory_zone(state)
    imm = zone.get("immutable") if isinstance(zone.get("immutable"), dict) else {}
    scope["immutable_lattice_ids"] = [str(x) for x in (imm.get("lattice_ids") or []) if x]
    return scope


def lattices_for_scope(index: dict[str, Any], scope: dict[str, Any]) -> list[str]:
    """Filter classified entries for a memory scope (shadow bind set)."""
    domains = set(scope.get("semantic_domains") or [])
    want_episodic = bool(scope.get("explicit_episodic"))
    out: list[str] = []
    for row in index.get("entries") or []:
        if not isinstance(row, dict):
            continue
        lid = str(row.get("lattice_id") or "")
        if row.get("memory_subkind") == "episodic" and want_episodic:
            out.append(lid)
            continue
        dom = str(row.get("domain") or "")
        if dom and dom in domains:
            out.append(lid)
    extra = set(scope.get("active_theory_lattice_ids") or [])
    for lid in scope.get("immutable_lattice_ids") or []:
        extra.add(str(lid))
    if extra:
        out = sorted(set(out) | extra)
    else:
        out = sorted(out)
    return out


def _default_client_for_tract(tract: str, zones: dict[str, Any]) -> str:
    for zone_id, cfg in zones.items():
        if not isinstance(cfg, dict):
            continue
        allow = [str(t).lower() for t in (cfg.get("tract_allowlist") or [])]
        if "*" in allow:
            continue
        if tract in allow:
            return str(zone_id)
    if tract == "math":
        return "logical"
    if tract in {"social", "discuss", "grammar", "explain", "journal", "recall", "rewrite"}:
        return "linguistic"
    return "executive"


def shadow_tract_report(index: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    """Compare math vs discuss scoped lattice sets (acceptance preview)."""
    math_scope = memory_resolve_scopes(doc, tract="math", client_zone="logical")
    discuss_scope = memory_resolve_scopes(doc, tract="discuss", client_zone="linguistic")
    math_lats = set(lattices_for_scope(index, math_scope))
    discuss_lats = set(lattices_for_scope(index, discuss_scope))
    phrase_in_math = sorted(lid for lid in math_lats if "phrase" in lid.lower() or lid.startswith("L3_"))
    math_in_discuss = sorted(lid for lid in discuss_lats if "math" in lid.lower() or lid.startswith("schema-"))
    return {
        "math": {
            "scope": math_scope,
            "lattice_count": len(math_lats),
            "phrase_leak": phrase_in_math[:8],
            "phrase_leak_n": len(phrase_in_math),
        },
        "discuss": {
            "scope": discuss_scope,
            "lattice_count": len(discuss_lats),
            "math_leak": math_in_discuss[:8],
            "math_leak_n": len(math_in_discuss),
        },
        "overlap_count": len(math_lats & discuss_lats),
    }
