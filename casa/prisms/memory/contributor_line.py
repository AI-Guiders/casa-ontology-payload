#!/usr/bin/env python3
"""Contributor line — attribution on journal + sleep artifacts (moral north star P2)."""

from __future__ import annotations

import os
import re
from typing import Any

_CONTRIBUTOR_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_ENV_KEYS = ("CASA_CONTRIBUTOR_LINE", "CONTRIBUTOR_LINE")


def normalize_contributor_line(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if not s or not _CONTRIBUTOR_RE.fullmatch(s):
        raise ValueError(f"invalid contributor_line: {raw!r}")
    return s


def resolve_contributor_line(explicit: str | None = None) -> str | None:
    """Explicit arg wins; else CASA_CONTRIBUTOR_LINE / CONTRIBUTOR_LINE env."""
    if explicit:
        return normalize_contributor_line(explicit)
    for key in _ENV_KEYS:
        raw = os.environ.get(key)
        if raw and str(raw).strip():
            return normalize_contributor_line(raw)
    return None


def stamp_journal_entry(row: dict[str, Any], contributor_line: str) -> dict[str, Any]:
    """Top-level + meta mirror for journal rows."""
    cl = normalize_contributor_line(contributor_line)
    out = dict(row)
    out["contributor_line"] = cl
    meta = dict(out.get("meta") or {})
    meta.setdefault("contributor_line", cl)
    out["meta"] = meta
    return out


def record_contributor_line_meta(state: dict, contributor_line: str) -> None:
    """Rolling set on state.meta for sleep / honesty artifacts."""
    cl = normalize_contributor_line(contributor_line)
    meta = state.setdefault("meta", {})
    lines: list[str] = [str(x) for x in (meta.get("contributor_lines") or []) if x]
    if cl not in lines:
        lines.append(cl)
    meta["contributor_lines"] = lines[-16:]


def collect_contributor_lines(state: dict, store_dir=None, *, journal_limit: int = 24) -> list[str]:
    """Union: state.meta + recent journal entries."""
    seen: set[str] = set()
    ordered: list[str] = []
    meta = state.get("meta") or {}
    for raw in meta.get("contributor_lines") or []:
        try:
            cl = normalize_contributor_line(str(raw))
        except ValueError:
            continue
        if cl not in seen:
            seen.add(cl)
            ordered.append(cl)
    env = resolve_contributor_line()
    if env and env not in seen:
        seen.add(env)
        ordered.append(env)
    if store_dir is not None:
        from pathlib import Path

        from casa.prisms.memory.agent_journal import search_journal_entries

        rows = search_journal_entries(Path(store_dir), limit=max(1, journal_limit))
        for row in reversed(rows):
            cl_raw = row.get("contributor_line") or (row.get("meta") or {}).get("contributor_line")
            if not cl_raw:
                continue
            try:
                cl = normalize_contributor_line(str(cl_raw))
            except ValueError:
                continue
            if cl not in seen:
                seen.add(cl)
                ordered.append(cl)
    return ordered


def attach_contributor_lines(report: dict[str, Any], state: dict, store_dir=None) -> dict[str, Any]:
    lines = collect_contributor_lines(state, store_dir)
    if lines:
        report["contributor_lines"] = lines
    return report
