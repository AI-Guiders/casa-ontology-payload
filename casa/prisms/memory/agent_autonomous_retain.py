#!/usr/bin/env python3
"""Autonomous Self retain — verified predict → workbook draft → check → confirmed."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.agent_workbook import workbook_check, workbook_write
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick
from casa.prisms.tick.surprise_policy import normalize_cue


def retain_key(cue: str, expect: str | None) -> str:
    return f"{normalize_cue(cue)}|{expect or ''}"


def _already_retained(store_dir: Path, key: str) -> bool:
    for row in search_journal_entries(store_dir, limit=0):
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        if meta.get("retain_key") == key:
            return True
        if meta.get("status") == "confirmed" and meta.get("expect") == key.split("|", 1)[-1]:
            tc = meta.get("test_cues") or []
            if tc and retain_key(str(tc[0]), key.split("|", 1)[-1] or None) == key:
                return True
    return False


def _retain_prose(cue: str, expect: str, scene: str) -> str:
    if expect.startswith("math.pattern.emerged."):
        return f"Считаю ряд «{cue}» — выученный count-by паттерн."
    if expect.startswith("math.struct.emerged."):
        return f"Упорядоченная последовательность для «{cue}»."
    return f"«{cue}» → {expect}" + (f" — {scene}" if scene else "")


def _self_name_after_confirm(
    store_dir: Path,
    *,
    cue: str,
    expect: str,
    scene: str,
    retain_key: str,
) -> dict[str, Any] | None:
    if not (expect.startswith("math.pattern.emerged.") or expect.startswith("math.struct.emerged.")):
        return None
    name = f"count-by:{cue}" if "," in cue else f"pattern:{expect[-8:]}"
    return workbook_write(
        store_dir,
        kind="note",
        text=_retain_prose(cue, expect, scene),
        concepts=[expect],
        test_cues=[cue],
        expect=expect,
        notebook="count-by",
        tags=["self_name", "emergent"],
        extra_meta={"retain_key": retain_key, "self_name": name, "scene": scene},
    )


def _infer_notebook(expect: str | None, scene: str) -> str | None:
    if expect and (expect.startswith("math.pattern.emerged.") or expect.startswith("math.struct.emerged.")):
        return "count-by"
    if expect and expect.startswith("math.pattern.count_by_"):
        return "count-by"
    if expect and expect.startswith("math.num."):
        if "skip" in scene or "двой" in scene or "трой" in scene or "пят" in scene or "сем" in scene:
            return "count-by"
        return "numerals"
    if expect and expect.startswith("math.op."):
        return "math-ops"
    return None


def predict_modality(bundle: dict | None) -> str:
    if bundle and bundle.get("math_tokens"):
        return "schema"
    return "t9"


def self_verify_predict(
    state: dict,
    cue: str,
    *,
    bundle: dict | None,
    modality: str | None = None,
) -> dict[str, Any] | None:
    """Predict → re-check with expect=hypothesis (no teacher). Returns tick2 if self-confirmed."""
    mod = modality or predict_modality(bundle)
    tick1 = predict_tick(state, cue, modality=mod, bundle=bundle)
    hyp = (tick1.get("predict") or {}).get("hypothesis")
    if not hyp:
        return None
    tick2 = predict_tick(state, cue, modality=mod, expect=hyp, bundle=bundle)
    if tick2.get("verdict") not in ("pass", "provisional"):
        return None
    unbound = (tick2.get("predict") or {}).get("unbound_operators") or []
    if unbound:
        return None
    return tick2


def retain_verified_predict(
    store_dir: Path,
    state: dict,
    *,
    cue: str,
    expect: str,
    hypothesis: str | None = None,
    bundle: dict | None = None,
    scene: str = "",
    notebook: str | None = None,
    source: str = "autonomous",
    persist: bool = True,
) -> dict[str, Any] | None:
    """Write Self draft and run workbook_check when predict matches expect."""
    hyp = hypothesis or expect
    if hyp != expect:
        return None

    key = retain_key(cue, expect)
    if _already_retained(store_dir, key):
        return {"skipped": True, "reason": "already_retained", "retain_key": key}

    nb = notebook or _infer_notebook(expect, scene)
    text = _retain_prose(cue, expect, scene)

    row = workbook_write(
        store_dir,
        kind="hypothesis",
        text=text,
        concepts=[expect] if expect.startswith(("math.", "lang.", "custom.")) else [expect],
        test_cues=[cue],
        expect=expect,
        notebook=nb,
        tags=[source],
        extra_meta={"retain_key": key, "scene": scene, "source": source},
    )
    check = workbook_check(store_dir, state, row["id"], bundle, persist=False)
    self_name = None
    if check.get("status") == "confirmed":
        self_name = _self_name_after_confirm(
            store_dir,
            cue=cue,
            expect=expect,
            scene=scene,
            retain_key=key,
        )
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state)

    rep = {
        "retain_key": key,
        "journal_id": row["id"],
        "status": check.get("status"),
        "passes": check.get("passes"),
        "total": check.get("total"),
        "source": source,
        "self_name": self_name,
    }
    cue_s = str(cue or "").strip()
    from casa.prisms.visual.bridge_math import VIS_CUE_PREFIX, frame_id_from_vis_cue, self_promote_vis_math_bridge

    if cue_s.startswith(VIS_CUE_PREFIX) and str(expect).startswith("math.") and check.get("status") == "confirmed":
        frame_id = frame_id_from_vis_cue(cue_s)
        promoted = self_promote_vis_math_bridge(
            state,
            frame_id=frame_id,
            math_cid=str(expect),
            provenance="self_retain",
        )
        if promoted:
            rep["vis_math_bridge"] = promoted
            if persist:
                mark_runtime_dirty(state)
                save_runtime_state(store_dir, state)

    return rep


def retain_from_check_row(
    store_dir: Path,
    state: dict,
    bundle: dict,
    row: dict[str, Any],
    *,
    source: str = "teacher_check",
    persist: bool = False,
) -> dict[str, Any] | None:
    if row.get("verdict") != "pass":
        return None
    expect = row.get("expect")
    if not expect:
        return None
    return retain_verified_predict(
        store_dir,
        state,
        cue=str(row.get("cue") or ""),
        expect=str(expect),
        hypothesis=row.get("hypothesis"),
        bundle=bundle,
        scene=str(row.get("label") or row.get("cue") or ""),
        source=source,
        persist=persist,
    )


def maybe_autonomous_retain_tick(
    store_dir: Path,
    state: dict,
    *,
    cue: str,
    bundle: dict | None,
    modality: str | None = None,
    teacher_expect: str | None = None,
    persist: bool = False,
) -> dict[str, Any] | None:
    """Tick hook: teacher expect or self-verify → Self retain."""
    mod = modality or predict_modality(bundle)
    if teacher_expect:
        tick = predict_tick(state, cue, modality=mod, expect=teacher_expect, bundle=bundle)
        if tick.get("verdict") != "pass":
            return None
        return retain_verified_predict(
            store_dir,
            state,
            cue=cue,
            expect=teacher_expect,
            hypothesis=(tick.get("predict") or {}).get("hypothesis"),
            bundle=bundle,
            source="tick_teacher",
            persist=persist,
        )

    tick = self_verify_predict(state, cue, bundle=bundle, modality=mod)
    if tick is None:
        return None
    hyp = (tick.get("predict") or {}).get("hypothesis")
    if not hyp:
        return None
    return retain_verified_predict(
        store_dir,
        state,
        cue=cue,
        expect=str(hyp),
        hypothesis=hyp,
        bundle=bundle,
        source="tick_self_verify",
        persist=persist,
    )


def retain_passing_checks(
    store_dir: Path,
    state: dict,
    bundle: dict,
    check_rows: list[dict[str, Any]],
    *,
    persist: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in check_rows:
        rep = retain_from_check_row(store_dir, state, bundle, row, persist=False)
        if rep and not rep.get("skipped"):
            out.append(rep)
    if persist and out:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state)
    return out
