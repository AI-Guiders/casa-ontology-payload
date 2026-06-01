#!/usr/bin/env python3
"""[LAB] Autonomous macro tick — внешняя телеметрия, не prod life (`agent_life`)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_autonomous_retain import (
    maybe_autonomous_retain_tick,
    predict_modality,
    self_verify_predict,
)
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.agent_notebook import ensure_agent_notebook
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick


def macro_tick(
    store_dir: Path,
    state: dict,
    cue: str,
    *,
    bundle: dict | None = None,
    modality: str | None = None,
    teacher_expect: str | None = None,
    self_verify: bool = False,
    notebook: str | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """One autonomous T: thalamus+router (via predict_tick) → predict → optional Self retain."""
    mod = modality or predict_modality(bundle)
    retain = None
    if teacher_expect:
        retain = maybe_autonomous_retain_tick(
            store_dir,
            state,
            cue=cue,
            bundle=bundle,
            modality=mod,
            teacher_expect=teacher_expect,
            persist=False,
        )
    elif self_verify:
        tick_sv = self_verify_predict(state, cue, bundle=bundle, modality=mod)
        if tick_sv:
            hyp = (tick_sv.get("predict") or {}).get("hypothesis")
            if hyp:
                from casa.prisms.memory.agent_autonomous_retain import retain_verified_predict

                retain = retain_verified_predict(
                    store_dir,
                    state,
                    cue=cue,
                    expect=str(hyp),
                    hypothesis=str(hyp),
                    bundle=bundle,
                    notebook=notebook,
                    source="macro_tick_self_verify",
                    persist=False,
                )
    else:
        tick = predict_tick(state, cue, modality=mod, expect=teacher_expect, bundle=bundle)
        return {
            "cue": cue,
            "modality": mod,
            "verdict": tick.get("verdict"),
            "hypothesis": (tick.get("predict") or {}).get("hypothesis"),
            "retain": None,
            "tick": tick,
        }

    tick = predict_tick(state, cue, modality=mod, expect=teacher_expect, bundle=bundle)
    return {
        "cue": cue,
        "modality": mod,
        "verdict": tick.get("verdict"),
        "hypothesis": (tick.get("predict") or {}).get("hypothesis"),
        "expect": teacher_expect,
        "retain": retain,
        "tick": tick,
    }


def autonomous_rehearse(
    store_dir: Path,
    *,
    cues: list[dict[str, Any]],
    bundle: dict | None = None,
    modality: str | None = None,
    notebook: str | None = "autonomous",
    create_notebook: bool = True,
    notebook_title: str = "",
    self_verify: bool = False,
    persist: bool = True,
    write_summary: bool = True,
) -> dict[str, Any]:
    """Run macro ticks on cues; retain passing predictions into agent workbook."""
    store_dir = store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])

    nb_meta = None
    if notebook and create_notebook:
        nb_meta = ensure_agent_notebook(
            store_dir,
            notebook,
            title=notebook_title or notebook,
            intro=None,
        )

    mod = modality or predict_modality(bundle)
    ticks: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []

    for row in cues:
        cue = str(row.get("cue") or "")
        expect = str(row.get("expect") or "") or None
        if not cue:
            continue
        rep = macro_tick(
            store_dir,
            state,
            cue,
            bundle=bundle,
            modality=mod,
            teacher_expect=expect if not self_verify else None,
            self_verify=self_verify and not expect,
            notebook=notebook,
            persist=False,
        )
        ticks.append(rep)
        retain = rep.get("retain")
        if retain and not retain.get("skipped"):
            retained.append(retain)

    passed = sum(1 for t in ticks if t.get("verdict") == "pass" or (t.get("retain") or {}).get("status") == "confirmed")
    summary_id = None
    if write_summary and notebook:
        lines = [f"Автономная rehearsal: {passed}/{len(ticks)} pass."]
        for t in ticks[:12]:
            hyp = t.get("hypothesis") or "?"
            lines.append(f"  «{t.get('cue')}» → {hyp}")
        if len(ticks) > 12:
            lines.append(f"  … ещё {len(ticks) - 12} cue")
        rem = agent_remember(
            store_dir,
            state,
            {
                "kind": "observation",
                "text": "\n".join(lines),
                "notebook": notebook,
                "tags": ["autonomous", "rehearse"],
                "data": {"passed": passed, "total": len(ticks), "modality": mod},
            },
            scope=notebook,
            persist=False,
        )
        summary_id = rem.get("journal_id")

    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)

    return {
        "store_dir": str(store_dir),
        "modality": mod,
        "notebook": notebook,
        "notebook_bootstrap": nb_meta,
        "ticks": len(ticks),
        "passed": passed,
        "retained": len(retained),
        "retain_rows": retained,
        "summary_journal_id": summary_id,
        "field_version": state.get("field_version"),
        "trace": ticks,
    }


def rehearse_class_manifest(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
    notebook: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    class_dir = class_dir.resolve()
    manifest = json.loads((class_dir / manifest_name).read_text(encoding="utf-8"))
    bundle_path = class_dir / str(manifest.get("bundle") or "kb-math-palochki-v1.bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8")) if bundle_path.is_file() else None
    class_id = str(manifest.get("class_id") or class_dir.name)
    nb = notebook or class_id
    cues = list(manifest.get("probe") or [])
    rep = autonomous_rehearse(
        store_dir,
        cues=cues,
        bundle=bundle,
        notebook=nb,
        notebook_title=f"Rehearse: {class_id}",
        **kwargs,
    )
    rep["class_id"] = class_id
    rep["class_dir"] = str(class_dir)
    return rep
