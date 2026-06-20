#!/usr/bin/env python3
# ruff: noqa: E402
"""Agent life zone — вся жизнь агента (wake → tick → sleep → journal → ltm).

Host только поднимает/гасит процесс (`agent_wake` / Ctrl+C). Смысл каждого tick — внутри:
predict, retain, curiosity, Kolb, hippo, SN — зона агента, не host и не teacher.

Lab-инструменты (`agent_autonomous.py`) — внешняя телеметрия для разработки, не prod life.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from casa.prisms.memory.agent_curiosity import agent_first_wake_note, agent_self_tick, self_drive_state
from casa.prisms.memory.agent_prism import load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store, runtime_checkpoint_paths
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.control.fpn_state import WorkingMemory, load_session, save_session
from casa.prisms.tick.orchestrator import LearningTickConfig, run_learning_tick

_SESSION_VERSION = 1
_DEFAULT_DISPLAY_NAME = "Нейманн"
_IDLE_SLICE_S = 0.05
_DEFAULT_PERSIST_EVERY = 8


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_agent_session(store_dir: Path) -> dict[str, Any]:
    path = runtime_checkpoint_paths(store_dir)["agent_session"]
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                legacy = data.get("kolb")
                if isinstance(legacy, dict) and "self_drive" not in data:
                    data["self_drive"] = {
                        "kolb_runs": legacy.get("runs"),
                        "last_count_row_end": legacy.get("last_count_row_end"),
                        "last_emergent": legacy.get("last_emergent"),
                    }
                return data
        except json.JSONDecodeError:
            pass
    return {
        "schema_version": _SESSION_VERSION,
        "started_at": _utc_now(),
        "macro_ticks": 0,
        "hippo_sleep_threshold": 8,
        "self_drive": {"kolb_runs": 0},
    }


def save_agent_session(store_dir: Path, session: dict[str, Any]) -> None:
    from casa.prisms.shared.field_write import _write_json

    path = runtime_checkpoint_paths(store_dir)["agent_session"]
    session["updated_at"] = _utc_now()
    _write_json(path, session)


def resolve_agent_bundle(store_dir: Path) -> dict[str, Any] | None:
    """Снимок bundle после прошлого ingest — часть опыта агента, не host oracle."""
    bundles = store_dir / "bundles"
    if not bundles.is_dir():
        return None
    for path in sorted(bundles.glob("*.bundle.json")):
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _display_name_from_store(store_dir: Path) -> str:
    manifest = store_dir / "memory_manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            name = data.get("display_name") or data.get("agent_name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        except json.JSONDecodeError:
            pass
    return _DEFAULT_DISPLAY_NAME


def agent_life_tick(
    store_dir: Path,
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Один quantum жизни агента (сейчас: idle → self_drive; позже: внешний cue, relay)."""
    from casa.body.completion_ingest import ingest_body_completions_on_tick

    body_ingest = ingest_body_completions_on_tick(store_dir, state, session)
    rep = agent_self_tick(store_dir, state, session, bundle=bundle)
    if body_ingest.get("ingested") or body_ingest.get("committed"):
        rep["body_completions"] = body_ingest
    return rep


@dataclass
class AgentRuntime:
    store_dir: Path
    state: dict
    session: dict[str, Any]
    bundle: dict[str, Any] | None
    wm: WorkingMemory | None = None


def _reactor_life_config(*, partner_turn: bool) -> LearningTickConfig:
    """One continuous life engine — partner cue or idle heartbeat."""
    return LearningTickConfig(
        act_rollout=False,
        surprise_episode=True,
        remember_on_surprise=True,
        retain_on_verified_predict=True,
        sleep_every=0,
        agent_self_drive=True,
        goal_from_surprise=True,
        metacog_gate=True,
        spacing_on_wake=False,
        tick_log=partner_turn,
        retro_after_sleep=True,
    )


def load_unified_agent_runtime(store_dir: Path) -> AgentRuntime:
    """Load store for unified reactor: SN/CEN macro ticks + teacher inbox + partner channel."""
    store_dir = store_dir.resolve()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.domain.store_recovery import maybe_recover_store_on_wake

    maybe_recover_store_on_wake(store_dir)
    state = resolve_ingest_state(store_dir, None)
    from casa.domain.subject_mode import apply_subject_profile

    apply_subject_profile(store_dir, state)
    state = ensure_prisms(state)
    load_agent_prism(store_dir, state)
    bundle = resolve_agent_bundle(store_dir)
    session = load_agent_session(store_dir)
    wm = load_session(store_dir)
    if int(session.get("macro_ticks") or 0) == 0 and wm.tick == 0:
        agent_first_wake_note(store_dir, state, display_name=_display_name_from_store(store_dir))
    state["_defer_runtime_persist"] = True
    return AgentRuntime(store_dir=store_dir, state=state, session=session, bundle=bundle, wm=wm)


def persist_unified_runtime(
    runtime: AgentRuntime,
    *,
    force: bool = True,
    sync_ltm: bool = False,
) -> dict[str, Any]:
    if runtime.wm is not None:
        save_session(runtime.store_dir, runtime.wm)
        runtime.session["macro_ticks"] = int(runtime.wm.tick)
    return persist_agent_runtime(runtime, force=force, sync_ltm=sync_ltm)


def _run_unified_life_tick(
    runtime: AgentRuntime,
    *,
    user_query: str | None,
    partner_turn: bool,
    partner_turn_kind: str = "chat",
) -> dict[str, Any]:
    from casa.body.completion_ingest import ingest_body_completions_on_tick

    assert runtime.wm is not None
    body_ingest = ingest_body_completions_on_tick(runtime.store_dir, runtime.state, runtime.session)
    report, wm_next, state_out = run_learning_tick(
        store_dir=runtime.store_dir,
        user_query=user_query,
        wm=runtime.wm,
        partner_turn_kind=partner_turn_kind,
        config=_reactor_life_config(partner_turn=partner_turn),
        state=runtime.state,
    )
    runtime.wm = wm_next
    runtime.state = state_out
    runtime.session["macro_ticks"] = int(wm_next.tick)
    if body_ingest.get("ingested") or body_ingest.get("committed"):
        report = {**report, "body_completions": body_ingest}
    return report


def run_life_tick(
    runtime: AgentRuntime,
    *,
    user_query: str | None = None,
    partner_turn: bool = False,
    partner_turn_kind: str = "chat",
) -> dict[str, Any]:
    """One unified macro tick — all active percept channels on this step."""
    return _run_unified_life_tick(
        runtime,
        user_query=user_query,
        partner_turn=partner_turn,
        partner_turn_kind=partner_turn_kind,
    )


def poll_partner_text_tract(
    runtime: AgentRuntime,
    *,
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    """Drain pending afferent partner text → macro tick → efferent reply."""
    from casa.body.text_tract import (
        complete_efferent,
        extract_dialogue_reply,
        fail_afferent_cue,
        poll_pending_afferent,
        write_pulse,
    )

    cue = poll_pending_afferent(runtime.store_dir)
    if cue is None:
        return False

    cue_id = str(cue.get("id") or "")
    text = str(cue.get("text") or "").strip()
    kind = str(cue.get("kind") or "chat")
    if emit:
        emit(
            {
                "afferent": cue_id,
                "tract_id": cue.get("tract_id"),
                "wire": cue.get("wire"),
                "text_len": len(text),
            }
        )
    life_t = int(runtime.wm.tick) if runtime.wm is not None else 0
    write_pulse(
        runtime.store_dir,
        macro_tick=life_t,
        sn_mode="partner_turn",
        extra={"phase": "partner_start", "cue_id": cue_id},
    )
    try:
        report = _run_unified_life_tick(
            runtime,
            user_query=text,
            partner_turn=True,
            partner_turn_kind=kind,
        )
        reply = extract_dialogue_reply(report)
        complete_efferent(
            runtime.store_dir,
            cue_id,
            reply_text=reply,
            tick=int(report.get("tick") or 0),
            report=report,
        )
        if runtime.wm is not None:
            write_pulse(
                runtime.store_dir,
                macro_tick=int(runtime.wm.tick),
                sn_mode=str(report.get("sn_mode") or ""),
                extra={"phase": "partner_done", "cue_id": cue_id},
            )
        if emit:
            emit({"efferent": cue_id, "tick": report.get("tick"), "reply_len": len(reply)})
    except Exception as err:  # noqa: BLE001 — daemon must survive one bad turn
        fail_afferent_cue(runtime.store_dir, cue_id, error=repr(err))
        if runtime.wm is not None:
            write_pulse(
                runtime.store_dir,
                macro_tick=int(runtime.wm.tick),
                sn_mode="error",
                extra={"phase": "partner_error", "cue_id": cue_id},
            )
        if emit:
            emit({"tract_error": cue_id, "error": repr(err)})
    return True


poll_text_tract = poll_partner_text_tract


def unified_agent_reactor_loop(
    store_dir: Path,
    *,
    poll_inbox: Callable[[AgentRuntime], bool] | None = None,
    poll_ms: int = 500,
    persist_every: int = _DEFAULT_PERSIST_EVERY,
    idle_slice_s: float = _IDLE_SLICE_S,
) -> None:
    """Continuous agent-life: partner channel + teacher inbox + idle SN/CEN ticks."""
    from casa.body.text_tract import write_pulse

    write_pulse(
        store_dir,
        macro_tick=0,
        sn_mode="boot",
        extra={"phase": "loading"},
    )
    print(json.dumps({"life": "loading_store", "mode": "unified"}, ensure_ascii=False), flush=True)
    runtime = load_unified_agent_runtime(store_dir)
    write_pulse(
        store_dir,
        macro_tick=int(runtime.wm.tick) if runtime.wm is not None else 0,
        sn_mode="ready",
        extra={"phase": "ready"},
    )
    print(
        json.dumps(
            {
                "life": "ready",
                "macro_ticks": runtime.session.get("macro_ticks"),
                "wm_tick": runtime.wm.tick if runtime.wm else None,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    quanta = 0
    try:
        while True:
            if poll_partner_text_tract(runtime, emit=_emit_life_event):
                _safe_persist_unified(runtime, sync_ltm=False, reason="partner")
                continue

            if poll_inbox is not None and poll_inbox(runtime):
                _safe_persist_unified(runtime, sync_ltm=True, reason="inbox")
                continue

            report = _run_unified_life_tick(runtime, user_query=None, partner_turn=False)
            quanta += 1
            if runtime.wm is not None:
                write_pulse(
                    runtime.store_dir,
                    macro_tick=int(runtime.wm.tick),
                    sn_mode=str(report.get("sn_mode") or ""),
                    extra={"idle_quanta": quanta},
                )
            if quanta % max(1, persist_every) == 0:
                _safe_persist_unified(runtime, sync_ltm=False, reason="tick")

            time.sleep(max(0.05, idle_slice_s, poll_ms / 1000.0))
    except KeyboardInterrupt:
        runtime.session["stopped"] = "host_interrupt"
        _safe_persist_unified(runtime, sync_ltm=False, reason="interrupt")


def _emit_life_event(event: dict[str, Any]) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def _safe_persist_unified(runtime: AgentRuntime, *, sync_ltm: bool, reason: str) -> None:
    try:
        persist_unified_runtime(runtime, force=True, sync_ltm=sync_ltm)
    except (PermissionError, TimeoutError, OSError) as err:
        print(
            json.dumps(
                {"persist_skipped": reason, "error": repr(err)},
                ensure_ascii=False,
            ),
            flush=True,
        )


def load_agent_runtime(store_dir: Path) -> AgentRuntime:
    """Load store once — shared by life ticks and inbox ingest in one process."""
    store_dir = store_dir.resolve()
    from casa.domain.store_recovery import maybe_recover_store_on_wake

    maybe_recover_store_on_wake(store_dir)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    load_agent_prism(store_dir, state)
    bundle = resolve_agent_bundle(store_dir)
    session = load_agent_session(store_dir)
    if int(session.get("macro_ticks") or 0) == 0:
        agent_first_wake_note(store_dir, state, display_name=_display_name_from_store(store_dir))
    return AgentRuntime(store_dir=store_dir, state=state, session=session, bundle=bundle)


def persist_agent_runtime(
    runtime: AgentRuntime,
    *,
    force: bool = True,
    sync_ltm: bool = False,
) -> dict[str, Any]:
    save_agent_session(runtime.store_dir, runtime.session)
    mark_runtime_dirty(runtime.state)
    return save_runtime_state(
        runtime.store_dir,
        runtime.state,
        force=force,
        thin=True,
        sync_ltm_on_save=sync_ltm,
    )


def agent_live_loop(
    store_dir: Path,
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None,
    stop_after: int | None = None,
    idle_slice_s: float = _IDLE_SLICE_S,
    persist_checkpoint: bool = True,
    persist_every: int = 1,
) -> tuple[list[dict[str, Any]], bool]:
    """Жизненный цикл агента до stop_after quanta или Ctrl+C."""
    trace: list[dict[str, Any]] = []
    quanta = 0
    persisted_last = False
    every = max(1, persist_every)
    try:
        while stop_after is None or quanta < stop_after:
            trace.append(agent_life_tick(store_dir, state, session, bundle=bundle))
            quanta += 1
            at_boundary = stop_after is not None and quanta >= stop_after
            if persist_checkpoint and (quanta % every == 0 or at_boundary):
                save_agent_session(store_dir, session)
                mark_runtime_dirty(state)
                save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)
                persisted_last = True
            else:
                persisted_last = False
            if stop_after is None or quanta < stop_after:
                time.sleep(idle_slice_s)
    except KeyboardInterrupt:
        session["stopped"] = "host_interrupt"
    return trace, persisted_last


def agent_wake(
    store_dir: Path,
    *,
    stop_after: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Единственная prod-точка для host: загрузить store → агент живёт сам."""
    store_dir = store_dir.resolve()
    from casa.domain.store_recovery import maybe_recover_store_on_wake

    store_recovery = maybe_recover_store_on_wake(store_dir)
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    load_agent_prism(store_dir, state)
    bundle = resolve_agent_bundle(store_dir)
    session = load_agent_session(store_dir)

    if int(session.get("macro_ticks") or 0) == 0:
        agent_first_wake_note(store_dir, state, display_name=_display_name_from_store(store_dir))

    trace, persisted_last = agent_live_loop(
        store_dir,
        state,
        session,
        bundle=bundle,
        stop_after=stop_after,
        persist_every=1,
    )

    if persist and not persisted_last:
        save_agent_session(store_dir, session)
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)

    drive = self_drive_state(session)
    return {
        "store_dir": str(store_dir),
        "store_recovery": store_recovery,
        "macro_ticks": session.get("macro_ticks"),
        "last_self_drive": session.get("last_self_drive"),
        "self_drive": {
            "kolb_runs": drive.get("kolb_runs"),
            "last_emergent": drive.get("last_emergent"),
        },
        "field_version": state.get("field_version"),
        "quanta_this_wake": len(trace),
        "trace": trace,
    }


def default_agent_wake(store_dir: Path | None = None, **kwargs: Any) -> dict[str, Any]:
    return agent_wake(store_dir or default_agent_store(), **kwargs)


def agent_reactor_loop(
    store_dir: Path,
    *,
    poll_inbox: Callable[[AgentRuntime], bool],
    poll_ms: int = 500,
    persist_every: int = _DEFAULT_PERSIST_EVERY,
    idle_slice_s: float = _IDLE_SLICE_S,
) -> None:
    """Single-thread life + teacher inbox on one in-memory runtime."""
    print(json.dumps({"life": "loading_store"}, ensure_ascii=False), flush=True)
    runtime = load_agent_runtime(store_dir)
    print(json.dumps({"life": "ready", "macro_ticks": runtime.session.get("macro_ticks")}, ensure_ascii=False), flush=True)
    quanta = 0
    try:
        while True:
            if poll_inbox(runtime):
                _safe_persist(runtime, sync_ltm=True, reason="inbox")
                continue

            agent_life_tick(runtime.store_dir, runtime.state, runtime.session, bundle=runtime.bundle)
            quanta += 1
            if quanta % max(1, persist_every) == 0:
                _safe_persist(runtime, sync_ltm=False, reason="tick")

            time.sleep(max(0.05, idle_slice_s, poll_ms / 1000.0))
    except KeyboardInterrupt:
        runtime.session["stopped"] = "host_interrupt"
        _safe_persist(runtime, sync_ltm=False, reason="interrupt")


def _safe_persist(runtime: AgentRuntime, *, sync_ltm: bool, reason: str) -> None:
    try:
        persist_agent_runtime(runtime, force=True, sync_ltm=sync_ltm)
    except (PermissionError, TimeoutError, OSError) as err:
        print(
            json.dumps(
                {"persist_skipped": reason, "error": repr(err)},
                ensure_ascii=False,
            ),
            flush=True,
        )
