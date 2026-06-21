#!/usr/bin/env python3
"""Extract math.num.* |names| lang.word.* from co-occurrence in episodic scene (sleep)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.memory.f0_extract_gate import episode_surprise_gated, record_extract_provenance
from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links

_NAMES_SCENE = re.compile(r"ru:\s*([^|]+)\|\s*en:\s*(.+)$", re.I)
_HEARD_SCENE = re.compile(r"heard:\s*(.+)$", re.I)
_RU_HEAD = re.compile(r"([\u0400-\u04ff]+)")
_EN_HEAD = re.compile(r"([a-z]+(?:-[a-z]+)?)", re.I)


def _bundle_lang_words(bundle: dict | None) -> set[str]:
    if not bundle:
        return set()
    return {
        str(c.get("concept_id") or "")
        for c in bundle.get("claims") or []
        if str(c.get("concept_id") or "").startswith("lang.word.")
    }


def _lang_word_id(bundle: dict | None, surface: str) -> str | None:
    w = surface.strip().lower().replace(" ", "_")
    if not w:
        return None
    known = _bundle_lang_words(bundle)
    for cand in (f"lang.word.{w}", f"lang.word.{surface.strip()}"):
        if cand in known:
            return cand
    # Derive a lang.word concept for a taught scene word that is not in the curated
    # set. parse_bilingual_numeral_scene yields only the PRIMARY ru/en word, which is
    # an explicit teacher signal — so naming it generalizes bilingual vocabulary
    # beyond the hand-authored words (the linear-authoring ceiling the curriculum
    # exists to break) without admitting noise from scene decompositions.
    return f"lang.word.{w}"


def parse_bilingual_numeral_scene(scene: str) -> tuple[str | None, str | None]:
    """Experience surface: «ru: … | en: …» or trailing «heard: …» (rich medium hook)."""
    raw = str(scene or "").strip()
    heard = _HEARD_SCENE.search(raw)
    if heard:
        raw = heard.group(1).strip()
    m = _NAMES_SCENE.search(raw)
    if not m:
        return None, None
    ru_text = m.group(1).strip()
    if "—" in ru_text:
        ru_head = ru_text.split("—", 1)[0].strip()
        ru_m = _RU_HEAD.search(ru_head)
        ru_w = ru_m.group(1) if ru_m else None
    else:
        ru_all = _RU_HEAD.findall(ru_text)
        ru_w = ru_all[-1] if ru_all else None
    en = _EN_HEAD.findall(m.group(2))
    en_w = en[0].lower() if en else None
    return ru_w, en_w


def names_edges_on_field(lattices: dict[str, dict], lattice_id: str) -> set[str]:
    if lattice_id not in lattices:
        return set()
    dec = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    return {e for e in dec.get("edges") or [] if "|names|" in e}


def extract_emergent_names_from_episodes(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    bundle: dict | None,
    state: dict | None = None,
    *,
    lattice_id: str = "schema-math",
    copies: int = 4,
) -> list[dict[str, Any]]:
    """Co-presented numeral + spoken/written word in scene → names edge on F0."""
    if lattice_id not in lattices:
        return []
    existing = names_edges_on_field(lattices, lattice_id)
    pending_links: list[dict[str, str]] = []
    reports: list[dict[str, Any]] = []
    provenance_eps: list[str] = []

    for ep in episodes or []:
        if not episode_surprise_gated(ep):
            continue
        if ep.get("kind") not in (None, "surface"):
            continue
        cid = str(ep.get("concept_id") or "")
        if not cid:
            continue
        ru_w, en_w = parse_bilingual_numeral_scene(str(ep.get("scene") or ""))
        # a bilingual "ru: X | en: Y" scene is the gate — names mint for ANY taught
        # concept that carries one, not only numerals (general vocabulary)
        if not (ru_w or en_w):
            continue
        for surface in (en_w, ru_w):
            if not surface:
                continue
            dst = _lang_word_id(bundle, surface)
            if not dst:
                continue
            edge = f"{cid}|names|{dst}"
            if edge in existing:  # the edge-string set already dedupes (O(1)); the
                continue          # former `link in pending_links` list scan was O(n^2)
            pending_links.append({"src": cid, "relation": "names", "dst": dst})
            existing.add(edge)
            if ep.get("id"):
                provenance_eps.append(str(ep["id"]))
            reports.append(
                {
                    "kind": "emergent_names",
                    "concept_id": cid,
                    "word": dst,
                    "episode_id": ep.get("id"),
                    "cue": ep.get("cue"),
                }
            )

    if pending_links:
        minted = mint_episode_links(lattices, lattice_id=lattice_id, links=pending_links, copies=copies)
        if state is not None:
            record_extract_provenance(
                state,
                f"names:{reports[0]['concept_id']}",
                episode_ids=sorted(set(provenance_eps)),
                kind="emergent_names",
            )
        for rep in reports:
            rep["minted"] = True
        return [{**reports[0], "links": minted, "count": len(reports), "provenance_episodes": provenance_eps}] if reports else []
    return reports
