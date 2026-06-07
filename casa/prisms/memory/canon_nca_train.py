#!/usr/bin/env python3
"""Canon lattice NCA — agent/host enqueue after field sync; drain via worker/body extension."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.memory.lexicon_shard import set_nca_model
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.nca_codec import tokens_from_lattice
from casa.prisms.shared.canon_lattice_policy import canon_nca_lattice_ids, is_canon_nca_lattice
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.nca_registry import (
    lattice_token_count,
    lattice_train_fingerprint,
    load_registry,
    mark_lattice_trained,
    model_path_for_lattice,
    repair_smoke_ratio,
    save_registry,
)
from casa.prisms.shared.nca_train_defaults import damage_defaults, epoch_budget, field_edge, windowed_train_config
from casa.prisms.shared.store_layout import nca_lattice_dir, rel_to_repo

TRAIN_COMPLETE_NAME = "train_complete.json"
CANON_NCA_FUNCTION_ID = "tool.memory.run_canon_nca"


def _train_complete_path(store_dir: Path, lattice_id: str) -> Path:
    return nca_lattice_dir(store_dir, lattice_id) / TRAIN_COMPLETE_NAME


def read_train_complete(store_dir: Path, lattice_id: str) -> dict[str, Any] | None:
    path = _train_complete_path(store_dir, lattice_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def write_train_complete(store_dir: Path, row: dict[str, Any]) -> Path:
    lid = canonical_lattice_id(str(row.get("lattice_id") or ""))
    path = _train_complete_path(store_dir, lid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def clear_train_complete(store_dir: Path, lattice_id: str) -> None:
    path = _train_complete_path(store_dir, lattice_id)
    if path.is_file():
        path.unlink()


def emit_canon_nca_completion_percept(store_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
    from casa.body.completion_percept import append_body_completion_percept

    lid = str(row.get("lattice_id") or "")
    ok = bool(row.get("trained"))
    summary = f"canon NCA train complete: {lid}" if ok else f"canon NCA train skipped: {lid}"
    return append_body_completion_percept(
        store_dir,
        function_id=CANON_NCA_FUNCTION_ID,
        ok=ok,
        summary=summary,
        structured=row,
        provenance={"lattice_id": lid, "awaiting_agent_commit": row.get("awaiting_agent_commit", True)},
    )


def agent_commit_canon_nca_completion(
    store_dir: Path,
    state: dict,
    lattice_id: str,
    *,
    persist: bool = False,
) -> dict[str, Any]:
    """Agent accepts body train artifact — updates in-memory state + registry; optional persist."""
    from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    lid = canonical_lattice_id(lattice_id)
    marker = read_train_complete(store_dir, lid)
    if marker is None:
        model = nca_lattice_dir(store_dir, lid) / "model.pt"
        if not model.is_file():
            return {"committed": False, "lattice_id": lid, "reason": "no_train_complete"}
        model_rel = rel_to_repo(model)
        repair_ratio = None
    else:
        model_rel = str(marker.get("model_path") or "")
        repair_ratio = marker.get("repair_ratio")

    lat = memory_lattices(state).get(lid) or {}
    if model_rel:
        set_nca_model(state, lid, model_rel)
    model_path = model_path_for_lattice(store_dir, state, lid)
    ratio = repair_ratio
    if ratio is None and model_path is not None:
        ratio = repair_smoke_ratio(lat, model_path)
    entry = mark_lattice_trained(store_dir, state, lid, repair_ratio=ratio, lattice=lat)
    clear_train_complete(store_dir, lid)
    mark_runtime_dirty(state)
    rep: dict[str, Any] = {
        "committed": True,
        "lattice_id": lid,
        "model_path": model_rel or rel_to_repo(model_path),
        "registry": entry,
    }
    if persist:
        rep["persist"] = save_runtime_state(store_dir, state, force=True, sync_ltm_on_save=False)
    return rep


def agent_commit_pending_canon_nca(
    store_dir: Path,
    state: dict,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """Drain train_complete markers — agent-owned checkpoint commit."""
    store_dir = store_dir.resolve()
    commits: list[dict[str, Any]] = []
    for lid in sorted(canon_nca_lattice_ids()):
        if read_train_complete(store_dir, lid) is None:
            continue
        rep = agent_commit_canon_nca_completion(store_dir, state, lid, persist=False)
        if rep.get("committed"):
            commits.append(rep)
    out: dict[str, Any] = {"committed": len(commits), "results": commits}
    if persist and commits:
        from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

        mark_runtime_dirty(state)
        out["persist"] = save_runtime_state(store_dir, state, force=True, sync_ltm_on_save=False)
    return out


def _train_script_path() -> Path:
    return REPO_ROOT / "tools" / "train_memory_nca.py"


def _utc_request_row(
    lattice_id: str,
    *,
    reason: str,
    actor: str,
    journal_id: str | None = None,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "lattice_id": lattice_id,
        "reason": reason[:120],
        "actor": actor,
        "journal_id": journal_id,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


def enqueue_canon_nca_train(
    store_dir: Path,
    lattice_id: str,
    *,
    reason: str,
    actor: str = "agent",
    journal_id: str | None = None,
) -> dict[str, Any]:
    """Queue NCA train/repair for a canon shelf (agent act after promote, or host bootstrap)."""
    lid = canonical_lattice_id(str(lattice_id or "").strip())
    if not lid:
        raise ValueError("lattice_id is required")
    if not is_canon_nca_lattice(lid):
        raise ValueError(f"lattice {lid!r} is not a canon NCA target")

    reg = load_registry(store_dir)
    pending = list(reg.get("pending") or [])
    if lid not in pending:
        pending.append(lid)
    reg["pending"] = pending

    requests: list[dict[str, Any]] = list(reg.get("pending_requests") or [])
    row = _utc_request_row(lid, reason=reason, actor=actor, journal_id=journal_id)
    requests = [r for r in requests if str(r.get("lattice_id")) != lid]
    requests.append(row)
    reg["pending_requests"] = requests[-64:]
    save_registry(store_dir, reg)
    return {"enqueued": True, "lattice_id": lid, "reason": reason, "actor": actor}


def agent_requests_nca_train_after_canon(
    store_dir: Path,
    lattice_id: str,
    *,
    reason: str = "agent_canon_promote",
    journal_id: str | None = None,
) -> dict[str, Any]:
    """Agent decided promote → same act schedules NCA repair for that shelf."""
    return enqueue_canon_nca_train(
        store_dir,
        lattice_id,
        reason=reason,
        actor="agent",
        journal_id=journal_id,
    )


def host_requests_nca_train_after_bootstrap(
    store_dir: Path,
    lattice_id: str,
    *,
    reason: str = "host_bootstrap_seed",
) -> dict[str, Any]:
    return enqueue_canon_nca_train(store_dir, lattice_id, reason=reason, actor="host")


def lattice_needs_nca_train(
    state: dict,
    store_dir: Path,
    lattice_id: str,
    *,
    min_tokens: int = 4,
) -> tuple[bool, list[str]]:
    """Whether canon shelf should be trained/retrained."""
    lid = canonical_lattice_id(lattice_id)
    if not is_canon_nca_lattice(lid):
        return False, ["not_canon_nca"]
    lat = memory_lattices(state).get(lid) or {}
    tok = len(tokens_from_lattice(lat))
    if tok < min_tokens:
        return False, ["min_tokens"]

    reg = load_registry(store_dir)
    if lid in set(reg.get("pending") or []):
        return True, ["pending_request"]

    meta = dict(reg.get("lattices", {}).get(lid) or {})
    model = model_path_for_lattice(store_dir, state, lid)
    reasons: list[str] = []
    if model is None:
        reasons.append("missing_model")
    cur_fp = lattice_train_fingerprint(lat)
    trained_fp = meta.get("train_fingerprint")
    if meta and trained_fp and cur_fp != trained_fp:
        reasons.append("content_drift")
    trained_tok = int(meta.get("token_count_at_train") or -1)
    if meta and tok != trained_tok:
        reasons.append("token_count_drift")
    return bool(reasons), reasons


def train_one_nca_lattice(
    store_dir: Path,
    state: dict,
    lattice_id: str,
    *,
    epochs: int | None = None,
    device: str = "cpu",
    allow_missing_tool: bool = True,
    agent_commit: bool = False,
) -> dict[str, Any]:
    """Train model.pt for one lattice. Default: body artifact only — agent commits checkpoint."""
    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    lid = canonical_lattice_id(lattice_id)
    lat = memory_lattices(state).get(lid) or {}
    tok = len(tokens_from_lattice(lat))
    row: dict[str, Any] = {
        "lattice_id": lid,
        "token_count": tok,
        "trained": False,
        "skipped": False,
    }
    if tok < 4:
        row["skipped"] = True
        row["reason"] = "min_tokens"
        return row

    script = _train_script_path()
    if not script.is_file():
        if allow_missing_tool:
            row["skipped"] = True
            row["reason"] = "train_tool_missing"
            return row
        raise FileNotFoundError(script)

    out_dir = nca_lattice_dir(store_dir, lid)
    store_nca = out_dir
    model = out_dir / "model.pt"
    force = os.environ.get("CASA_FORCE_NCA_RETRAIN", "").strip().lower() in ("1", "true", "yes")
    if not agent_commit and read_train_complete(store_dir, lid) is not None:
        row["skipped"] = True
        row["reason"] = "awaiting_agent_commit"
        row["awaiting_agent_commit"] = True
        return row

    needs, reasons = lattice_needs_nca_train(state, store_dir, lid)
    if model.is_file() and not force and not needs:
        if agent_commit:
            from casa.prisms.shared.nca_registry import clear_pending

            clear_pending(store_dir, [lid])
        row["skipped"] = True
        row["reason"] = "already_trained"
        return row

    ep = epochs if epochs is not None else epoch_budget("sss_shard_incremental")
    edge = field_edge("sss_lattice")
    win = windowed_train_config(field_edge=edge)
    dmg = damage_defaults()
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(script),
        "--store-dir",
        str(store_dir),
        "--lattice-id",
        lid,
        "--epochs",
        str(ep),
        "--device",
        device,
        "--out-dir",
        str(out_dir),
        "--save-model",
        "--tile-w",
        str(win.tile_w),
        "--tile-h",
        str(win.tile_h),
        "--stride-x",
        str(win.stride_x),
        "--stride-y",
        str(win.stride_y),
        "--ghost",
        str(win.ghost),
        "--windows-per-batch",
        str(win.windows_per_batch),
        "--max-windows-per-batch",
        str(win.max_windows_per_batch),
        "--damage-patches",
        str(dmg["damage_patches"]),
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
    if model.is_file():
        model_rel = rel_to_repo(model)
        ratio = repair_smoke_ratio(lat, model)
        row["trained"] = True
        row["model_path"] = model_rel
        row["repair_ratio"] = ratio
        if agent_commit:
            set_nca_model(state, lid, model_rel or str(model))
            row["registry"] = mark_lattice_trained(store_dir, state, lid, repair_ratio=ratio, lattice=lat)
        else:
            row["awaiting_agent_commit"] = True
            write_train_complete(
                store_dir,
                {
                    "lattice_id": lid,
                    "model_path": model_rel,
                    "repair_ratio": ratio,
                    "token_count": tok,
                    "train_fingerprint": lattice_train_fingerprint(lat),
                },
            )
            emit_canon_nca_completion_percept(store_dir, row)
    return row


def run_pending_canon_nca_trains(
    store_dir: Path,
    state: dict,
    *,
    max_jobs: int = 1,
    device: str = "cpu",
    allow_missing_tool: bool = True,
    agent_commit: bool = False,
) -> dict[str, Any]:
    """Drain canon NCA queue — body writes artifacts; agent owns registry/field_state commit."""
    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    reg = load_registry(store_dir)
    pending = [canonical_lattice_id(str(x)) for x in (reg.get("pending") or [])]
    canon_pending = [lid for lid in pending if is_canon_nca_lattice(lid)]
    results: list[dict[str, Any]] = []
    jobs = 0
    for lid in canon_pending:
        if jobs >= max(1, int(max_jobs)):
            break
        needs, reasons = lattice_needs_nca_train(state, store_dir, lid)
        if not needs and lid not in set(reg.get("pending") or []):
            continue
        try:
            rep = train_one_nca_lattice(
                store_dir,
                state,
                lid,
                device=device,
                allow_missing_tool=allow_missing_tool,
                agent_commit=agent_commit,
            )
        except subprocess.CalledProcessError as exc:
            rep = {"lattice_id": lid, "trained": False, "error": str(exc), "reasons": reasons}
        rep["reasons"] = reasons
        results.append(rep)
        if rep.get("trained") or (rep.get("skipped") and rep.get("reason") == "already_trained"):
            jobs += 1
        elif rep.get("skipped") and rep.get("reason") == "train_tool_missing":
            break

    return {
        "ran": len(results),
        "trained": sum(1 for r in results if r.get("trained")),
        "pending_before": len(canon_pending),
        "results": results,
    }


def list_canon_nca_status(state: dict, store_dir: Path) -> dict[str, Any]:
    """Inspect canon shelves + NCA registry for CLI/debug."""
    state = ensure_prisms(state)
    reg = load_registry(store_dir)
    rows: list[dict[str, Any]] = []
    for lid in sorted(canon_nca_lattice_ids()):
        lat = memory_lattices(state).get(lid) or {}
        tok = lattice_token_count(state, lid) if lat else 0
        needs, reasons = lattice_needs_nca_train(state, store_dir, lid) if lat else (False, ["no_lattice"])
        meta = dict(reg.get("lattices", {}).get(lid) or {})
        awaiting = read_train_complete(store_dir, lid) is not None
        rows.append(
            {
                "lattice_id": lid,
                "token_count": tok,
                "needs_train": needs,
                "reasons": reasons,
                "pending": lid in set(reg.get("pending") or []),
                "awaiting_agent_commit": awaiting,
                "model_path": meta.get("model_path"),
                "last_trained_at": meta.get("last_trained_at"),
            }
        )
    return {
        "canon_targets": sorted(canon_nca_lattice_ids()),
        "pending": list(reg.get("pending") or []),
        "pending_requests": list(reg.get("pending_requests") or []),
        "rows": rows,
    }
