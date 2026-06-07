#!/usr/bin/env python3
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
