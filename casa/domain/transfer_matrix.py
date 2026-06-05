#!/usr/bin/env python3
"""Load CASA cross-prism transfer matrix (ADR-0021 R1 / R2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
MATRIX_REL = Path("design/matrices/matrix-casa-cross-prism-transfer-v1.json")


def transfer_matrix_path(custom: Path | None = None) -> Path:
    if custom is not None:
        return custom.resolve()
    return (REPO_ROOT / MATRIX_REL).resolve()


def load_transfer_matrix(path: Path | None = None) -> dict[str, Any]:
    p = transfer_matrix_path(path)
    if not p.is_file():
        return {"schema_version": "casa_transfer_matrix_v1", "routes": [], "content_prism_stubs": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _subst_locale(match: dict[str, str], locale: str) -> dict[str, str]:
    loc = (locale or "ru").strip().lower()
    out: dict[str, str] = {}
    for k, v in match.items():
        if v == "{locale}":
            out[k] = loc
        else:
            out[k] = str(v).strip().lower()
    return out


def routes_from_transfer_matrix(*, locale: str = "ru", path: Path | None = None) -> list[Any]:
    from casa.domain.routing import Route

    data = load_transfer_matrix(path)
    out: list[Route] = []
    for row in data.get("routes") or []:
        if not isinstance(row, dict):
            continue
        raw_match = row.get("match") or {}
        if not isinstance(raw_match, dict):
            continue
        hint = row.get("lattice_hint")
        out.append(
            Route(
                match=_subst_locale({str(k): str(v) for k, v in raw_match.items() if v}, locale),
                route_kind="knowledge",
                target_prism=str(row.get("target_prism") or "prism_memory"),
                lattice_hint=str(hint) if hint else None,
                priority=int(row.get("priority") or 0),
            )
        )
    out.sort(key=lambda r: r.priority, reverse=True)
    return out


def content_prism_stubs(path: Path | None = None) -> list[dict[str, str]]:
    data = load_transfer_matrix(path)
    stubs: list[dict[str, str]] = []
    for row in data.get("content_prism_stubs") or []:
        if isinstance(row, dict) and row.get("prism_id"):
            stubs.append(
                {
                    "prism_id": str(row["prism_id"]),
                    "stack": str(row.get("stack") or "design/prisms/memory/stack.json"),
                }
            )
    return stubs
