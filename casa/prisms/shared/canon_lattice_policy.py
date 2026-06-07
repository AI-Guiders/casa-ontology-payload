#!/usr/bin/env python3
"""Canon lattice policy — bootstrap vs agent_canon (immutable-lattice canon v1)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id

_MAP_PATH = REPO_ROOT / "design" / "lattice-id-map.v1.json"
_STABILITY_BOOTSTRAP = "bootstrap_canon"
_STABILITY_AGENT = "agent_canon"


@lru_cache(maxsize=1)
def _map_doc() -> dict[str, Any]:
    if not _MAP_PATH.is_file():
        return {}
    return json.loads(_MAP_PATH.read_text(encoding="utf-8"))


def host_bootstrap_lattice_ids() -> frozenset[str]:
    canon = _map_doc().get("canon_immutable_lattices") or {}
    host = [canonical_lattice_id(str(x)) for x in (canon.get("host_bootstrap") or [])]
    planned = [canonical_lattice_id(str(x)) for x in (canon.get("planned_host_bootstrap") or [])]
    return frozenset(host + planned)


def agent_decides_canon() -> bool:
    canon = _map_doc().get("canon_immutable_lattices") or {}
    return bool(canon.get("agent_decides_canon", True))


def planned_agent_canon_lattices() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for lid, spec in (_map_doc().get("planned_lattices") or {}).items():
        if not isinstance(spec, dict):
            continue
        if str(spec.get("stability") or "") != _STABILITY_AGENT:
            continue
        out[canonical_lattice_id(str(lid))] = dict(spec)
    return out


def lattice_stability_class(lattice_id: str) -> str | None:
    lid = canonical_lattice_id(str(lattice_id or "").strip())
    if lid in host_bootstrap_lattice_ids():
        return _STABILITY_BOOTSTRAP
    spec = planned_agent_canon_lattices().get(lid)
    if spec:
        return _STABILITY_AGENT
    return None


def assert_agent_may_promote(lattice_id: str) -> dict[str, Any]:
    if not agent_decides_canon():
        raise ValueError("agent_decides_canon is disabled in lattice-id-map")
    lid = canonical_lattice_id(str(lattice_id or "").strip())
    if not lid:
        raise ValueError("lattice_id is required")
    if lid in host_bootstrap_lattice_ids():
        raise ValueError(f"bootstrap lattice {lid!r} is host-only; agent cannot promote into it")
    spec = planned_agent_canon_lattices().get(lid)
    if not spec:
        raise ValueError(
            f"lattice {lid!r} is not an agent_canon target; see planned_lattices in lattice-id-map.v1.json"
        )
    return spec


def concept_allowed_for_lattice(lattice_id: str, concept_id: str) -> bool:
    spec = planned_agent_canon_lattices().get(canonical_lattice_id(lattice_id)) or {}
    prefixes = [str(p) for p in (spec.get("concept_prefix") or spec.get("meta_prefix") or []) if p]
    if not prefixes and spec.get("meta_prefix"):
        prefixes = [str(spec["meta_prefix"]) + "."]
    cid = str(concept_id or "").strip()
    if not cid:
        return False
    if not prefixes:
        return True
    return any(cid.startswith(p) for p in prefixes)


def assert_concepts_for_lattice(lattice_id: str, concept_ids: list[str]) -> None:
    if not concept_ids:
        raise ValueError("promote requires at least one concept_id")
    for cid in concept_ids:
        if not concept_allowed_for_lattice(lattice_id, cid):
            raise ValueError(f"concept {cid!r} not allowed on lattice {lattice_id!r}")


def bootstrap_canon_lattice_ids() -> frozenset[str]:
    """Planned/bootstrap_canon lattices (e.g. morph-role-ru) — host seed, NCA repair."""
    out = set(host_bootstrap_lattice_ids())
    for lid, spec in (_map_doc().get("planned_lattices") or {}).items():
        if not isinstance(spec, dict):
            continue
        if str(spec.get("stability") or "") == _STABILITY_BOOTSTRAP:
            out.add(canonical_lattice_id(str(lid)))
    return frozenset(out)


def agent_canon_lattice_ids() -> frozenset[str]:
    return frozenset(planned_agent_canon_lattices().keys())


def canon_nca_lattice_ids(*, extra: frozenset[str] | None = None) -> frozenset[str]:
    """Immutable canon shelves that get 1 lattice → 1 NCA repair (ADR-0002)."""
    ids = set(bootstrap_canon_lattice_ids()) | set(agent_canon_lattice_ids())
    if extra:
        ids.update(extra)
    return frozenset(ids)


def is_canon_nca_lattice(lattice_id: str) -> bool:
    return canonical_lattice_id(str(lattice_id or "").strip()) in canon_nca_lattice_ids()
