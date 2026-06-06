#!/usr/bin/env python3
"""Paradigm clusters from phrase co-occurrence + LTM form coverage (ADR-0036)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
from casa.prisms.visual.bridge_lex import lex_concept_votes
from casa.prisms.visual.phrase_compose import load_phrase_events


def _slug(word: dict[str, Any]) -> str:
    return str(word.get("slug") or "").strip()


def _ensure(parent: dict[str, str], x: str) -> None:
    if x not in parent:
        parent[x] = x


def _union_find(parent: dict[str, str], x: str) -> str:
    _ensure(parent, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent: dict[str, str], a: str, b: str) -> None:
    _ensure(parent, a)
    _ensure(parent, b)
    ra, rb = _union_find(parent, a), _union_find(parent, b)
    if ra != rb:
        parent[rb] = ra


def paradigm_cluster_id(slugs: frozenset[str]) -> str:
    key = "|".join(sorted(slugs))
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"lang.paradigm.co.{digest}"


def co_occur_groups_from_events(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge word slugs that appear in the same phrase event (co-sleep hint)."""
    slugs: set[str] = set()
    for entry in entries:
        for w in entry.get("words") or []:
            s = _slug(w)
            if s:
                slugs.add(s)

    parent = {s: s for s in slugs}
    for entry in entries:
        event_slugs = [_slug(w) for w in entry.get("words") or [] if _slug(w)]
        for i, a in enumerate(event_slugs):
            for b in event_slugs[i + 1 :]:
                _union(parent, a, b)
        for ex in entry.get("examples") or []:
            if not isinstance(ex, dict):
                continue
            ex_slugs = [_slug(w) for w in ex.get("words") or [] if _slug(w)]
            for i, a in enumerate(ex_slugs):
                for b in ex_slugs[i + 1 :]:
                    _union(parent, a, b)
            lemma = str(ex.get("lemma") or "").strip()
            if lemma:
                for s in ex_slugs:
                    _union(parent, s, f"lemma:{lemma}")

    buckets: dict[str, list[str]] = {}
    for s in slugs:
        root = _union_find(parent, s)
        buckets.setdefault(root, []).append(s)

    groups: list[dict[str, Any]] = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        slug_set = frozenset(members)
        groups.append(
            {
                "cluster_id": paradigm_cluster_id(slug_set),
                "slugs": sorted(members),
                "size": len(members),
            }
        )
    groups.sort(key=lambda g: (-int(g["size"]), str(g["cluster_id"])))
    return groups


def form_known_in_ltm(state: dict, slug: str, *, min_votes: int = 2) -> bool:
    cid = canonical_lex_concept_id(f"lang.word.{slug}")
    return lex_concept_votes(state, cid, min_votes=min_votes) >= min_votes


def paradigm_ltm_report(
    state: dict,
    *,
    events_path: Path | str | None = None,
    min_votes: int = 2,
) -> dict[str, Any]:
    entries = load_phrase_events(events_path)
    groups = co_occur_groups_from_events(entries)
    rows: list[dict[str, Any]] = []
    for g in groups:
        known = {s: form_known_in_ltm(state, s, min_votes=min_votes) for s in g["slugs"]}
        rows.append(
            {
                **g,
                "known": known,
                "know_count": sum(1 for v in known.values() if v),
                "complete": all(known.values()),
            }
        )
    return {
        "total_clusters": len(rows),
        "complete_clusters": sum(1 for r in rows if r.get("complete")),
        "clusters": rows,
    }


def write_paradigm_report(
    state: dict,
    path: Path,
    *,
    events_path: Path | str | None = None,
) -> dict[str, Any]:
    report = paradigm_ltm_report(state, events_path=events_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
