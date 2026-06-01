#!/usr/bin/env python3
"""Autonomous Kolb cycle — agent-initiated «а что будет, если?» (CE → sleep → AE)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any, Literal

from casa.prisms.memory.agent_autonomous_engine import macro_tick
from casa.prisms.memory.agent_autonomous_retain import predict_modality, retain_verified_predict
from casa.prisms.memory.agent_journal import append_journal_entry
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.agent_notebook import ensure_agent_notebook
from casa.prisms.memory.f0_pattern_extract import (
    is_emergent_pattern_id,
    numeral_int_to_concept_id,
    numeral_surface_to_int,
    parse_comma_numeral_cue,
)
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

KolbPhase = Literal["concrete", "reflect", "abstract", "active"]


def plan_count_row_what_if(
    start: int = 0,
    end: int = 6,
    *,
    scene: str = "count_row:what_if",
) -> list[dict[str, Any]]:
    """Agent hypothesis: «а что будет, если считать start…end по одному?»"""
    if end <= start:
        raise ValueError("count row end must be > start")
    rows: list[dict[str, Any]] = []
    for value in range(start, end):
        cid = numeral_int_to_concept_id(value)
        if not cid:
            continue
        surface = str(value)
        rows.append(
            {
                "cue": surface,
                "correct": surface,
                "concept_id": cid,
                "scene": scene,
            }
        )
    return rows


def plan_cue_what_if(cues: list[str], *, scene: str = "what_if") -> list[dict[str, Any]]:
    """Open probes — no teacher expect; agent tries surface and records surprise."""
    return [{"cue": c.strip(), "scene": scene} for c in cues if c.strip()]


def _comma_probe_from_count_row(rows: list[dict[str, Any]]) -> str | None:
    values: list[int] = []
    for row in rows:
        v = numeral_surface_to_int(str(row.get("cue") or row.get("correct") or ""))
        if v is not None:
            values.append(v)
    if len(values) < 2:
        return None
    values.sort()
    return ", ".join(str(v) for v in values)


def _kolb_concrete_experience(
    store_dir: Path,
    state: dict,
    *,
    rows: list[dict[str, Any]],
    bundle: dict | None,
    modality: str,
    notebook: str | None,
) -> dict[str, Any]:
    ticks: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    surprises = 0

    for row in rows:
        cue = str(row.get("cue") or "")
        if not cue:
            continue
        tick = predict_tick(state, cue, modality=modality, bundle=bundle)
        hyp = (tick.get("predict") or {}).get("hypothesis") or ""
        verdict = tick.get("verdict")
        correct = str(row.get("correct") or row.get("expect") or "")
        concept_id = row.get("concept_id")
        scene = str(row.get("scene") or "what_if")
        correction_kind = None
        structure_tag = None
        semantic_ok = bool(concept_id and hyp == str(concept_id))
        if semantic_ok:
            pass
        elif correct and hyp and hyp != correct:
            correction_kind = "predict_surprise"
            structure_tag = "predict_mismatch"
            surprises += 1
        elif verdict not in ("pass", "provisional") and hyp:
            correction_kind = "predict_surprise"
            structure_tag = "predict_mismatch"
            surprises += 1

        ep = append_episode(
            state,
            cue=cue,
            surface_attempt=str(hyp or "?"),
            correct=correct or str(hyp or ""),
            lattice_id=str(row.get("lattice_id") or SCHEMA_MATH),
            concept_id=str(concept_id) if concept_id else None,
            bundle=bundle,
            scene=scene,
            correction_kind=correction_kind,
            structure_tag=structure_tag,
            episode_source="wake",
        )
        if ep:
            episodes.append(ep)
        ticks.append(
            {
                "cue": cue,
                "verdict": verdict,
                "hypothesis": hyp,
                "episode_id": (ep or {}).get("id"),
                "surprise": bool(correction_kind),
                "semantic_ok": semantic_ok,
            }
        )

    if notebook:
        agent_remember(
            store_dir,
            state,
            {
                "kind": "hypothesis",
                "text": _concrete_journal_text(rows, surprises),
                "notebook": notebook,
                "tags": ["kolb", "concrete", "what_if"],
                "data": {"surprises": surprises, "probes": len(ticks)},
            },
            scope=notebook,
            persist=False,
        )

    return {"ticks": ticks, "episodes": len(episodes), "surprises": surprises}


def _concrete_journal_text(rows: list[dict[str, Any]], surprises: int) -> str:
    scene = str(rows[0].get("scene") or "") if rows else ""
    if scene.startswith("count_row"):
        vals = [
            str(r.get("cue"))
            for r in rows
            if numeral_surface_to_int(str(r.get("cue") or "")) is not None
        ]
        span = f"{vals[0]}…{vals[-1]}" if len(vals) >= 2 else (vals[0] if vals else "?")
        return (
            f"А что будет, если посчитать ряд {span}? "
            f"Попробовал {len(rows)} шагов, сюрпризов: {surprises}."
        )
    cues = [str(r.get("cue")) for r in rows[:6]]
    tail = f" (+{len(rows) - 6})" if len(rows) > 6 else ""
    return f"А что будет, если: {', '.join(cues)}{tail}? Сюрпризов: {surprises}."


def _kolb_reflect_abstract(
    state: dict,
    *,
    bundle: dict | None,
) -> dict[str, Any]:
    sleep_rep = run_sleep(state, bundle)
    emergent: list[dict[str, Any]] = []
    for item in sleep_rep.get("items") or []:
        cid = item.get("concept_id") or (item.get("extract") or {}).get("concept_id")
        if cid and is_emergent_pattern_id(str(cid)):
            emergent.append(item)
    return {
        "sleep": sleep_rep,
        "merged": sleep_rep.get("merged"),
        "pending": sleep_rep.get("pending"),
        "emergent": emergent,
        "emergent_ids": [str(x.get("concept_id") or (x.get("extract") or {}).get("concept_id")) for x in emergent],
    }


def _kolb_active_experiment(
    store_dir: Path,
    state: dict,
    *,
    probe_rows: list[dict[str, Any]],
    bundle: dict | None,
    modality: str,
    notebook: str | None,
) -> dict[str, Any]:
    ticks: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []

    for row in probe_rows:
        cue = str(row.get("cue") or "")
        expect = str(row.get("expect") or "") or None
        if not cue:
            continue
        rep = macro_tick(
            store_dir,
            state,
            cue,
            bundle=bundle,
            modality=modality,
            teacher_expect=expect,
            self_verify=not expect,
            notebook=notebook,
            persist=False,
        )
        ticks.append(rep)
        retain = rep.get("retain")
        if retain and not retain.get("skipped"):
            retained.append(retain)
        elif not expect:
            tick = rep.get("tick") or {}
            hyp = (tick.get("predict") or {}).get("hypothesis")
            if hyp and tick.get("verdict") in ("pass", "provisional"):
                extra = retain_verified_predict(
                    store_dir,
                    state,
                    cue=cue,
                    expect=str(hyp),
                    hypothesis=str(hyp),
                    bundle=bundle,
                    notebook=notebook,
                    source="kolb_active",
                    persist=False,
                )
                if extra and not extra.get("skipped"):
                    retained.append(extra)

    passed = sum(1 for t in ticks if t.get("verdict") == "pass" or (t.get("retain") or {}).get("status") == "confirmed")
    return {"ticks": ticks, "passed": passed, "retained": retained}


def kolb_cycle(
    store_dir: Path,
    *,
    experiment: list[dict[str, Any]],
    bundle: dict | None = None,
    probe: list[dict[str, Any]] | None = None,
    notebook: str = "kolb",
    create_notebook: bool = True,
    persist: bool = True,
    write_journal: bool = True,
    state: dict | None = None,
) -> dict[str, Any]:
    """
    Full Kolb loop initiated by the agent (no teacher ingest).

    CE: predict + hippo episodes (count_row / what_if scenes)
    RO+AC: run_sleep → emergent math.pattern.emerged.*
    AE: re-probe (comma row or explicit cues) → Self retain
    """
    store_dir = store_dir.resolve()
    if state is None:
        boot = boot_store(store_dir, prefer_field_state=True)
        state = ensure_prisms(boot["state"])
    mod = predict_modality(bundle)

    if create_notebook:
        ensure_agent_notebook(store_dir, notebook, title="Kolb — что если?", intro=None)

    if write_journal:
        append_journal_entry(
            store_dir,
            {
                "kind": "note",
                "text": "Запускаю цикл Kolb: опыт → сон → проверка гипотезы.",
                "tags": ["kolb", "cycle_start"],
                "meta": {"notebook": notebook, "probes": len(experiment)},
            },
            domain=notebook,
        )

    concrete = _kolb_concrete_experience(
        store_dir,
        state,
        rows=experiment,
        bundle=bundle,
        modality=mod,
        notebook=notebook if write_journal else None,
    )

    reflect = _kolb_reflect_abstract(state, bundle=bundle)

    probe_rows = list(probe or [])
    if not probe_rows:
        comma = _comma_probe_from_count_row(experiment)
        if comma and parse_comma_numeral_cue(comma):
            probe_rows = [{"cue": comma}]
        else:
            probe_rows = [{"cue": str(r.get("cue") or "")} for r in experiment if r.get("cue")]

    active = _kolb_active_experiment(
        store_dir,
        state,
        probe_rows=probe_rows,
        bundle=bundle,
        modality=mod,
        notebook=notebook,
    )

    summary_id = None
    if write_journal and notebook:
        emergent_ids = reflect.get("emergent_ids") or []
        em_line = f" Emergent: {', '.join(emergent_ids)}." if emergent_ids else ""
        rem = agent_remember(
            store_dir,
            state,
            {
                "kind": "observation",
                "text": (
                    f"Kolb завершён: CE {concrete['episodes']} ep / {concrete['surprises']} surprise → "
                    f"sleep merged {reflect.get('merged')} → "
                    f"AE {active['passed']}/{len(active['ticks'])} pass.{em_line}"
                ),
                "notebook": notebook,
                "tags": ["kolb", "cycle_done"],
                "data": {
                    "concrete": concrete["surprises"],
                    "emergent": emergent_ids,
                    "active_passed": active["passed"],
                },
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
        "notebook": notebook,
        "modality": mod,
        "phases": {
            "concrete": concrete,
            "reflect": {
                "merged": reflect.get("merged"),
                "pending": reflect.get("pending"),
                "emergent_ids": reflect.get("emergent_ids"),
            },
            "active": {
                "passed": active["passed"],
                "total": len(active["ticks"]),
                "retained": len(active["retained"]),
            },
        },
        "summary_journal_id": summary_id,
        "field_version": state.get("field_version"),
    }


def kolb_count_row_what_if(
    store_dir: Path,
    *,
    start: int = 0,
    end: int = 6,
    bundle: dict | None = None,
    notebook: str = "kolb",
    state: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Shortcut: «а что будет, если считать start…end-1 по одному?»"""
    experiment = plan_count_row_what_if(start, end)
    comma = _comma_probe_from_count_row(experiment)
    probe = [{"cue": comma}] if comma else None
    rep = kolb_cycle(
        store_dir,
        experiment=experiment,
        bundle=bundle,
        probe=probe,
        notebook=notebook,
        state=state,
        **kwargs,
    )
    rep["count_row"] = {"start": start, "end": end}
    return rep


def kolb_open_what_if(
    store_dir: Path,
    *,
    cues: list[str],
    bundle: dict | None = None,
    notebook: str = "kolb",
    state: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Open «что если» on arbitrary cues (groups, ops, sticks)."""
    return kolb_cycle(
        store_dir,
        experiment=plan_cue_what_if(cues),
        bundle=bundle,
        notebook=notebook,
        state=state,
        **kwargs,
    )
