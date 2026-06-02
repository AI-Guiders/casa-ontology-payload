#!/usr/bin/env python3
"""Autonomous Kolb cycle — agent-initiated «а что будет, если?» (CE → sleep → AE).

Не привязан к curriculum, таблицам numerals или конкретным concept_id.
Агент подаёт cue (поверхность), predict → hippo → sleep (Extract) → re-probe.
Новые концепты — только то, что sleep вывел из опыта, не oracle в experiment rows.
"""

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
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.predict_tick import predict_tick

KolbPhase = Literal["concrete", "reflect", "abstract", "active"]
_DEFAULT_SCENE = "what_if"


def plan_what_if_probes(
    cues: list[str],
    *,
    scene: str = _DEFAULT_SCENE,
    lattice_id: str = SCHEMA_MATH,
) -> list[dict[str, Any]]:
    """Open probes — surfaces only; no teacher expect, no concept oracle."""
    rows: list[dict[str, Any]] = []
    for raw in cues:
        cue = str(raw or "").strip()
        if not cue:
            continue
        rows.append({"cue": cue, "scene": scene, "lattice_id": lattice_id})
    return rows


def _hypothesis_concept_id(hypothesis: str | None) -> str | None:
    hyp = str(hypothesis or "").strip()
    if not hyp or " " in hyp:
        return None
    if "." in hyp and not hyp[0].isdigit():
        return hyp
    return None


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
        scene = str(row.get("scene") or _DEFAULT_SCENE)
        lattice_id = str(row.get("lattice_id") or SCHEMA_MATH)
        expect = str(row.get("expect") or row.get("correct") or "").strip() or None
        correction_kind = None
        structure_tag = None

        if expect and hyp and hyp != expect:
            correction_kind = "predict_surprise"
            structure_tag = "predict_mismatch"
            surprises += 1
        elif verdict not in ("pass", "provisional"):
            correction_kind = "predict_surprise"
            structure_tag = "predict_mismatch"
            surprises += 1

        ep = append_episode(
            state,
            cue=cue,
            surface_attempt=str(hyp or "?"),
            correct=expect or str(hyp or ""),
            lattice_id=lattice_id,
            concept_id=_hypothesis_concept_id(hyp),
            bundle=bundle,
            scene=scene,
            correction_kind=correction_kind,
            structure_tag=structure_tag,
            form_extract_allowed=True,
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
    cues = [str(r.get("cue")) for r in rows if r.get("cue")][:8]
    tail = f" (+{len(rows) - len(cues)})" if len(rows) > len(cues) else ""
    joined = ", ".join(cues) if cues else "?"
    return f"А что будет, если: {joined}{tail}? Попробовал {len(rows)} раз, сюрпризов: {surprises}."


def _extract_item_concept_id(item: dict[str, Any]) -> str | None:
    cid = item.get("concept_id") or (item.get("extract") or {}).get("concept_id")
    return str(cid) if cid else None


def _kolb_reflect_abstract(
    state: dict,
    *,
    bundle: dict | None,
) -> dict[str, Any]:
    sleep_rep = run_sleep(state, bundle)
    extracted: list[dict[str, Any]] = []
    for item in sleep_rep.get("items") or []:
        cid = _extract_item_concept_id(item)
        if not cid:
            continue
        extracted.append({**item, "concept_id": cid})
    extracted_ids = [str(x["concept_id"]) for x in extracted]
    return {
        "sleep": sleep_rep,
        "merged": sleep_rep.get("merged"),
        "pending": sleep_rep.get("pending"),
        "extracted": extracted,
        "extracted_ids": extracted_ids,
        # compat alias for callers that looked for pattern hubs only
        "emergent_ids": extracted_ids,
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
        expect = str(row.get("expect") or row.get("correct") or "").strip() or None
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

    passed = sum(
        1
        for t in ticks
        if t.get("verdict") == "pass" or (t.get("retain") or {}).get("status") == "confirmed"
    )
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

    CE: predict + hippo episodes (surprise-gated, form_extract_allowed)
    RO+AC: run_sleep → whatever Extract mints from episodes
    AE: re-probe same or follow-up cues → Self retain
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
        probe_rows = [{"cue": str(r.get("cue") or ""), "scene": r.get("scene")} for r in experiment if r.get("cue")]

    active = _kolb_active_experiment(
        store_dir,
        state,
        probe_rows=probe_rows,
        bundle=bundle,
        modality=mod,
        notebook=notebook,
    )

    summary_id = None
    extracted_ids = reflect.get("extracted_ids") or []
    if write_journal and notebook:
        ex_line = f" Extract: {', '.join(extracted_ids)}." if extracted_ids else ""
        rem = agent_remember(
            store_dir,
            state,
            {
                "kind": "observation",
                "text": (
                    f"Kolb завершён: CE {concrete['episodes']} ep / {concrete['surprises']} surprise → "
                    f"sleep merged {reflect.get('merged')} → "
                    f"AE {active['passed']}/{len(active['ticks'])} pass.{ex_line}"
                ),
                "notebook": notebook,
                "tags": ["kolb", "cycle_done"],
                "data": {
                    "concrete": concrete["surprises"],
                    "extracted": extracted_ids,
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
                "extracted_ids": extracted_ids,
                "emergent_ids": extracted_ids,
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


def kolb_what_if(
    store_dir: Path,
    *,
    cues: list[str],
    bundle: dict | None = None,
    notebook: str = "kolb",
    state: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Open «что если» — произвольные cue-строки, без oracle."""
    return kolb_cycle(
        store_dir,
        experiment=plan_what_if_probes(cues),
        bundle=bundle,
        notebook=notebook,
        state=state,
        **kwargs,
    )


def kolb_open_what_if(
    store_dir: Path,
    *,
    cues: list[str],
    bundle: dict | None = None,
    notebook: str = "kolb",
    state: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Alias for kolb_what_if (legacy name)."""
    return kolb_what_if(
        store_dir,
        cues=cues,
        bundle=bundle,
        notebook=notebook,
        state=state,
        **kwargs,
    )


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
    """[LAB] Count surfaces as cue strings only — no concept_id oracle (host instrumentation)."""
    if end <= start:
        raise ValueError("count row end must be > start")
    cues = [str(v) for v in range(start, end)]
    rep = kolb_what_if(
        store_dir,
        cues=cues,
        bundle=bundle,
        notebook=notebook,
        state=state,
        **kwargs,
    )
    rep["lab_count_row"] = {"start": start, "end": end, "cues": cues}
    return rep
