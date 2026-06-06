#!/usr/bin/env python3
"""Hippo episode bind classes + concept_id resolve (ADR-0047)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from casa.prisms.control.tick import ControlExtensions

_CONCEPT_ID_RE = re.compile(
    r"(?:grapheme\.(?:cyrl|latn)\.[^\s,]+|lang\.word\.[a-z0-9]+|lang\.meta\.[a-zA-Z0-9_.]+"
    r"|math\.[a-z0-9_.]+|syllable\.[a-z0-9]+|skill\.[a-z0-9_.]+|vis\.[a-z0-9_.]+)",
    re.I,
)


class EpisodeBindClass(str, Enum):
    BINDABLE_SURPRISE = "bindable_surprise"
    BINDABLE_CORRECTION = "bindable_correction"
    OPEN_PROBE = "open_probe"
    RULE = "rule"


def primary_surprise_concept(
    control: ControlExtensions,
    *,
    user_query: str | None = None,
    bundle: dict | None = None,
) -> str | None:
    """Primary concept from Check surprise (shared with goal_emergent)."""
    from casa.domain.partner_cue_policy import resolve_primary_surprise_concept

    resolved = resolve_primary_surprise_concept(
        control, user_query=user_query, bundle=bundle
    )
    if resolved:
        return resolved
    for cid in control.surprise:
        s = str(cid).strip()
        if s.startswith(("lang.", "math.", "skill.", "vis.", "grapheme.", "syllable.")):
            return s
    return str(control.surprise[0]).strip() if control.surprise else None


def parse_concept_ids(text: str) -> list[str]:
    found = _CONCEPT_ID_RE.findall(str(text or ""))
    out: list[str] = []
    for cid in found:
        if cid not in out:
            out.append(cid)
    return out


def infer_bind_class(
    *,
    structure_tag: str | None,
    scene: str,
    concept_id: str | None,
    correct: str,
    kind: str = "surface",
) -> str:
    if kind == "rule":
        return EpisodeBindClass.RULE.value
    if (scene or "").strip() == "what_if" and not (concept_id or str(correct or "").strip()):
        return EpisodeBindClass.OPEN_PROBE.value
    if structure_tag == "predict_mismatch":
        return EpisodeBindClass.BINDABLE_SURPRISE.value
    if concept_id or str(correct or "").strip():
        return EpisodeBindClass.BINDABLE_CORRECTION.value
    return EpisodeBindClass.OPEN_PROBE.value


def counts_toward_load(ep: dict[str, Any]) -> bool:
    """open_probe episodes do not inflate cognitive load (ADR-0047)."""
    if ep.get("consolidated"):
        return False
    bind = str(ep.get("bind_class") or "")
    if bind == EpisodeBindClass.OPEN_PROBE.value:
        return False
    if ep.get("kind") in ("question", "hint") or ep.get("pending"):
        return False
    return True


def resolve_episode_concept_id(
    ep: dict[str, Any],
    bundle: dict | None,
    *,
    lattice_id: str | None = None,
) -> str | None:
    """Resolve concept_id before sleep merge (ADR-0047)."""
    cid = ep.get("concept_id")
    if cid:
        return str(cid)

    for field in ("correct", "surface_attempt", "cue"):
        parsed = parse_concept_ids(str(ep.get(field) or ""))
        if parsed:
            return parsed[0]

    if not bundle:
        return None

    from casa.prisms.memory.memory_prisms import concept_id_for_surface
    from casa.prisms.shared.lattice_names_v1 import SYLLABLES_RU, canonical_lattice_id

    lid = canonical_lattice_id(lattice_id or str(ep.get("lattice_id") or SYLLABLES_RU))
    for field in ("correct", "cue"):
        surface = str(ep.get(field) or "").strip()
        if not surface or "," in surface:
            continue
        resolved = concept_id_for_surface(bundle, surface, lattice_id=lid)
        if resolved:
            return resolved
    return None
