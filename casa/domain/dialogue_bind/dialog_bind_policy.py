"""Dialog bind policy from bundle claims — gated/open hub lists."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DESIGN_REL = Path("design") / "kb-dialog-bind.v1.json"


@lru_cache(maxsize=1)
def _design_claims() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parents[3] / _DESIGN_REL
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in raw.get("claims") or []:
        if isinstance(row, dict) and row.get("concept_id"):
            out[str(row["concept_id"])] = row
    return out


def _slots(cid: str, bundle: dict[str, Any] | None) -> dict[str, str]:
    if bundle:
        for row in bundle.get("claims") or []:
            if str(row.get("concept_id") or "") == cid:
                slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
                return {str(k): str(v) for k, v in slots.items()}
    claim = _design_claims().get(cid) or {}
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    return {str(k): str(v) for k, v in slots.items()}


def _split_pipe(raw: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in str(raw or "").split("|") if p.strip())


def gated_dialog_prefixes(bundle: dict[str, Any] | None = None) -> tuple[str, ...]:
    return _split_pipe(_slots("ru.meta.dialog.bind_policy", bundle).get("gated_hub_prefixes") or "")


def open_dialog_prefixes(bundle: dict[str, Any] | None = None) -> tuple[str, ...]:
    return _split_pipe(_slots("ru.meta.dialog.bind_policy", bundle).get("open_hub_prefixes") or "")


def _parse_weighted(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for part in _split_pipe(raw):
        if ":" in part:
            prefix, weight = part.rsplit(":", 1)
            try:
                out.append((prefix, int(weight)))
            except ValueError:
                continue
        else:
            out.append((part, 12))
    return out


def continuer_bind_demote(bundle: dict[str, Any] | None = None) -> list[tuple[str, int]]:
    raw = _slots("ru.meta.dialog.continuer_bind", bundle).get("bind_demote") or ""
    return _parse_weighted(raw)


def thread_carry_params(bundle: dict[str, Any] | None = None) -> dict[str, float | int | str]:
    slots = _slots("ru.meta.dialog.thread_carry", bundle)
    return {
        "carry_base": int(slots.get("carry_base") or 72),
        "decay_per_age": float(slots.get("decay_per_age") or 0.15),
        "ov_cap": int(slots.get("ov_cap") or 28),
        "ov_mul": int(slots.get("ov_mul") or 2),
        "continuer_linker": str(slots.get("continuer_linker") or "Про это"),
    }


def continuer_linker(bundle: dict[str, Any] | None = None) -> str:
    return str(thread_carry_params(bundle).get("continuer_linker") or "Про это")


def tone_register_slots(bundle: dict[str, Any] | None = None) -> dict[str, str]:
    return _slots("ru.meta.dialog.tone_register", bundle)


def hub_family_prefix(cid: str) -> str:
    """Longest matching gated/open prefix for a dialog concept id."""
    parts = str(cid or "").split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return str(cid or "")
