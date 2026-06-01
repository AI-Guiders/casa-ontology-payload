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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_curiosity import agent_first_wake_note, agent_self_tick, self_drive_state
from casa.prisms.memory.agent_prism import load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store, runtime_checkpoint_paths
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

_SESSION_VERSION = 1
_DEFAULT_DISPLAY_NAME = "Нейманн"
_IDLE_SLICE_S = 0.05


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
    path = runtime_checkpoint_paths(store_dir)["agent_session"]
    session["updated_at"] = _utc_now()
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    return agent_self_tick(store_dir, state, session, bundle=bundle)


def agent_live_loop(
    store_dir: Path,
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None,
    stop_after: int | None = None,
    idle_slice_s: float = _IDLE_SLICE_S,
) -> list[dict[str, Any]]:
    """Жизненный цикл агента до stop_after quanta или Ctrl+C."""
    trace: list[dict[str, Any]] = []
    quanta = 0
    try:
        while stop_after is None or quanta < stop_after:
            trace.append(agent_life_tick(store_dir, state, session, bundle=bundle))
            quanta += 1
            save_agent_session(store_dir, session)
            mark_runtime_dirty(state)
            save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)
            if stop_after is None or quanta < stop_after:
                time.sleep(idle_slice_s)
    except KeyboardInterrupt:
        session["stopped"] = "host_interrupt"
    return trace


def agent_wake(
    store_dir: Path,
    *,
    stop_after: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Единственная prod-точка для host: загрузить store → агент живёт сам."""
    store_dir = store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    load_agent_prism(store_dir, state)
    bundle = resolve_agent_bundle(store_dir)
    session = load_agent_session(store_dir)

    if int(session.get("macro_ticks") or 0) == 0:
        agent_first_wake_note(store_dir, state, display_name=_display_name_from_store(store_dir))

    trace = agent_live_loop(
        store_dir,
        state,
        session,
        bundle=bundle,
        stop_after=stop_after,
    )

    if persist:
        save_agent_session(store_dir, session)
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)

    drive = self_drive_state(session)
    return {
        "store_dir": str(store_dir),
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
