#!/usr/bin/env python3
"""Per-lattice NCA train registry + pending queue (incremental sleep repair v0)."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import l2_lexicon_lattice_ids, nca_model_registry  # type: ignore
from sss_nca_codec_v0 import tokens_from_lattice  # type: ignore
from store_layout_v0 import nca_lattice_dir, nca_train_registry_path, rel_to_repo  # type: ignore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_registry(*, store_id: str = "") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "nca_train_registry_v0",
        "store_id": store_id,
        "updated_at": _utc_now(),
        "field_version": 0,
        "pending": [],
        "lattices": {},
    }


def load_registry(store_dir: Path) -> dict[str, Any]:
    path = nca_train_registry_path(store_dir)
    if not path.is_file():
        return empty_registry(store_id=store_dir.name)
    reg = json.loads(path.read_text(encoding="utf-8"))
    reg.setdefault("pending", [])
    reg.setdefault("lattices", {})
    return reg


def save_registry(store_dir: Path, reg: dict[str, Any]) -> None:
    reg["updated_at"] = _utc_now()
    path = nca_train_registry_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lattice_token_count(state: dict, lattice_id: str) -> int:
    lat = memory_lattices(state).get(lattice_id) or {}
    return len(tokens_from_lattice(lat))


def model_path_for_lattice(store_dir: Path, state: dict, lattice_id: str) -> Path | None:
    reg = nca_model_registry(state).get(lattice_id)
    if reg:
        p = Path(reg)
        if p.is_file():
            return p
    fallback = nca_lattice_dir(store_dir, lattice_id) / "model.pt"
    if fallback.is_file():
        return fallback
    return None


def merge_pending(store_dir: Path, lattice_ids: list[str]) -> dict[str, Any]:
    reg = load_registry(store_dir)
    pending = list(reg.get("pending") or [])
    for lid in lattice_ids:
        if lid and lid not in pending:
            pending.append(lid)
    reg["pending"] = pending
    save_registry(store_dir, reg)
    return reg


def clear_pending(store_dir: Path, lattice_ids: list[str]) -> None:
    reg = load_registry(store_dir)
    drop = set(lattice_ids)
    reg["pending"] = [lid for lid in reg.get("pending") or [] if lid not in drop]
    save_registry(store_dir, reg)


def repair_smoke_ratio(lattice: dict, model_path: Path, *, seed: int = 42) -> float | None:
    from sss_nca_repair_v0 import nca_repair_lattice  # type: ignore

    if not model_path.is_file():
        return None
    try:
        rep = nca_repair_lattice(copy.deepcopy(lattice), model_path, seed=seed, device="cpu")
        return float(rep.get("recovery_ratio") or 0.0)
    except Exception:
        return None


def mark_lattice_trained(
    store_dir: Path,
    state: dict,
    lattice_id: str,
    *,
    repair_ratio: float | None = None,
) -> dict[str, Any]:
    reg = load_registry(store_dir)
    model = model_path_for_lattice(store_dir, state, lattice_id)
    entry: dict[str, Any] = {
        "last_trained_at": _utc_now(),
        "field_version_at_train": int(state.get("field_version") or 0),
        "token_count_at_train": lattice_token_count(state, lattice_id),
        "model_path": rel_to_repo(model),
    }
    if repair_ratio is not None:
        entry["last_repair_ratio"] = round(float(repair_ratio), 3)
        entry["last_repair_at"] = _utc_now()
    reg.setdefault("lattices", {})[lattice_id] = entry
    reg["pending"] = [lid for lid in reg.get("pending") or [] if lid != lattice_id]
    reg["field_version"] = int(state.get("field_version") or 0)
    reg["store_id"] = store_dir.name
    save_registry(store_dir, reg)
    return entry


def sync_registry_from_store(store_dir: Path, state: dict) -> dict[str, Any]:
    """Bootstrap registry entries for lattices that already have model.pt on disk."""
    reg = load_registry(store_dir)
    state = ensure_prisms(state)
    for lid in l2_lexicon_lattice_ids(state):
        model = model_path_for_lattice(store_dir, state, lid)
        if not model:
            continue
        cur = reg.get("lattices", {}).get(lid) or {}
        if cur.get("last_trained_at") and cur.get("token_count_at_train"):
            continue
        reg.setdefault("lattices", {})[lid] = {
            "last_trained_at": cur.get("last_trained_at") or _utc_now(),
            "field_version_at_train": int(cur.get("field_version_at_train") or state.get("field_version") or 0),
            "token_count_at_train": lattice_token_count(state, lid),
            "model_path": rel_to_repo(model),
            "synced_from_disk": True,
        }
    reg["field_version"] = int(state.get("field_version") or 0)
    reg["store_id"] = store_dir.name
    save_registry(store_dir, reg)
    return reg


def find_stale_shards(
    state: dict,
    store_dir: Path,
    *,
    repair_smoke: bool = False,
    min_recovery: float = 0.85,
    include_pending: bool = True,
    min_tokens: int = 8,
) -> list[dict[str, Any]]:
    state = ensure_prisms(state)
    reg = load_registry(store_dir)
    pending = set(reg.get("pending") or []) if include_pending else set()
    current_fv = int(state.get("field_version") or 0)
    rows: list[dict[str, Any]] = []

    for lid in l2_lexicon_lattice_ids(state):
        lat = memory_lattices(state).get(lid) or {}
        tok = lattice_token_count(state, lid)
        if tok < min_tokens:
            continue

        reasons: list[str] = []
        meta = dict(reg.get("lattices", {}).get(lid) or {})
        model = model_path_for_lattice(store_dir, state, lid)

        if model is None:
            reasons.append("missing_model")
        if lid in pending:
            reasons.append("pending_ingest")

        trained_fv = int(meta.get("field_version_at_train") or -1)
        trained_tok = int(meta.get("token_count_at_train") or -1)
        if meta and current_fv > trained_fv:
            reasons.append("field_version_drift")
        if meta and tok != trained_tok:
            reasons.append("token_count_drift")

        repair_ratio: float | None = None
        if repair_smoke and model is not None:
            repair_ratio = repair_smoke_ratio(lat, model)
            if repair_ratio is not None and repair_ratio < min_recovery:
                reasons.append("repair_smoke_fail")

        if not reasons:
            continue

        rows.append(
            {
                "lattice_id": lid,
                "reasons": reasons,
                "token_count": tok,
                "field_version": current_fv,
                "field_version_at_train": meta.get("field_version_at_train"),
                "token_count_at_train": meta.get("token_count_at_train"),
                "last_trained_at": meta.get("last_trained_at"),
                "model_path": rel_to_repo(model),
                "repair_ratio": repair_ratio,
            }
        )

    rows.sort(key=lambda r: r["lattice_id"])
    return rows
