#!/usr/bin/env python3
"""Idle self-drive — часть жизни агента (`agent_life`), когда нет внешнего cue."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.prism_wire import prism_hippo
from casa.prisms.memory.agent_autonomous_engine import macro_tick
from casa.prisms.memory.agent_autonomous_retain import predict_modality, self_verify_predict
from casa.prisms.memory.agent_kolb_cycle import kolb_count_row_what_if, kolb_open_what_if
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.f0_pattern_extract import is_emergent_pattern_id
from casa.prisms.memory.memory_prisms import append_episode, run_sleep
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH

# Agent's own rotation of open probes (not teacher curriculum).
_SELF_OPEN_PROBES: tuple[str, ...] = (
    "()",
    "(|)",
    "(||)",
    "(III)",
    "(IIIII)",
    "(||) + (||)",
    "(|||) - (||)",
)

_SELF_NOTEBOOK = "kolb"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pending_hippo(state: dict) -> list[dict[str, Any]]:
    return [ep for ep in prism_hippo(state).get("episodes") or [] if not ep.get("consolidated")]


def self_drive_state(session: dict[str, Any]) -> dict[str, Any]:
    """Mutable agent-owned drive ledger (in agent_session.json checkpoint)."""
    return session.setdefault("self_drive", {})


def agent_self_drive_step(state: dict, session: dict[str, Any]) -> dict[str, Any]:
    """What the agent chooses to do next when nothing external is asking."""
    drive = self_drive_state(session)
    pending = _pending_hippo(state)
    threshold = int(session.get("hippo_sleep_threshold") or 8)
    kolb_runs = int(drive.get("kolb_runs") or 0)

    if len(pending) >= threshold:
        return {"kind": "sleep", "reason": "hippo_full", "pending": len(pending)}

    if kolb_runs == 0:
        return {"kind": "kolb_count_row", "start": 0, "end": 6, "reason": "first_count_what_if"}

    last_end = drive.get("last_count_row_end")
    if drive.get("last_emergent") and isinstance(last_end, int) and last_end < 12:
        return {
            "kind": "kolb_count_row",
            "start": max(0, last_end - 2),
            "end": last_end + 3,
            "reason": "extend_count_row",
        }

    n = int(session.get("macro_ticks") or 0)
    cue = _SELF_OPEN_PROBES[n % len(_SELF_OPEN_PROBES)]
    if n % 4 == 0:
        return {"kind": "kolb_open", "cues": [cue], "reason": "open_what_if"}
    return {"kind": "what_if_probe", "cue": cue, "reason": "light_what_if"}


def _record_self_drive(session: dict[str, Any], rep: dict[str, Any]) -> None:
    drive = self_drive_state(session)
    drive["kolb_runs"] = int(drive.get("kolb_runs") or 0) + 1
    drive["last_at"] = _utc_now()
    cr = rep.get("count_row") or {}
    if cr:
        drive["last_count_row_end"] = cr.get("end")
    emergent = (rep.get("phases") or {}).get("reflect", {}).get("emergent_ids") or []
    if emergent:
        drive["last_emergent"] = emergent[-1]


def _what_if_probe(
    store_dir: Path,
    state: dict,
    *,
    cue: str,
    bundle: dict | None,
) -> dict[str, Any]:
    from casa.prisms.tick.predict_tick import predict_tick

    mod = predict_modality(bundle)
    tick = self_verify_predict(state, cue, bundle=bundle, modality=mod)
    surprise = False
    ep_id = None
    hyp: str | None = None

    if tick is not None:
        hyp = (tick.get("predict") or {}).get("hypothesis")
        macro_tick(
            store_dir,
            state,
            cue,
            bundle=bundle,
            modality=mod,
            self_verify=True,
            notebook=_SELF_NOTEBOOK,
            persist=False,
        )
    else:
        raw = predict_tick(state, cue, modality=mod, bundle=bundle)
        hyp = (raw.get("predict") or {}).get("hypothesis") or "?"
        surprise = raw.get("verdict") not in ("pass", "provisional")
        if surprise:
            ep = append_episode(
                state,
                cue=cue,
                surface_attempt=str(hyp),
                correct="",
                lattice_id=SCHEMA_MATH,
                bundle=bundle,
                scene="what_if",
                correction_kind="predict_surprise",
                structure_tag="predict_mismatch",
                episode_source="wake",
            )
            ep_id = (ep or {}).get("id")

    return {"kind": "what_if_probe", "cue": cue, "surprise": surprise, "episode_id": ep_id, "hypothesis": hyp}


def agent_self_tick(
    store_dir: Path,
    state: dict,
    session: dict[str, Any],
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """One internal macro-T when the agent is awake and self-directed."""
    action = agent_self_drive_step(state, session)
    kind = str(action.get("kind") or "")
    rep: dict[str, Any] = {"self_drive": action}

    if kind == "sleep":
        sleep_rep = run_sleep(state, bundle)
        rep["sleep"] = {"merged": sleep_rep.get("merged"), "pending": sleep_rep.get("pending")}
        emergent = [
            str(x.get("concept_id") or (x.get("extract") or {}).get("concept_id"))
            for x in sleep_rep.get("items") or []
            if is_emergent_pattern_id(str(x.get("concept_id") or (x.get("extract") or {}).get("concept_id") or ""))
        ]
        if emergent:
            rep["emergent_ids"] = emergent
    elif kind == "kolb_count_row":
        rep["kolb"] = kolb_count_row_what_if(
            store_dir,
            start=int(action.get("start") or 0),
            end=int(action.get("end") or 6),
            bundle=bundle,
            notebook=_SELF_NOTEBOOK,
            state=state,
            persist=False,
            write_journal=True,
        )
        _record_self_drive(session, rep["kolb"])
    elif kind == "kolb_open":
        rep["kolb"] = kolb_open_what_if(
            store_dir,
            cues=list(action.get("cues") or []),
            bundle=bundle,
            notebook=_SELF_NOTEBOOK,
            state=state,
            persist=False,
            write_journal=True,
        )
        _record_self_drive(session, rep["kolb"])
    elif kind == "what_if_probe":
        rep["probe"] = _what_if_probe(store_dir, state, cue=str(action.get("cue") or ""), bundle=bundle)
    else:
        rep["error"] = f"unknown self_drive kind: {kind}"

    session["macro_ticks"] = int(session.get("macro_ticks") or 0) + 1
    session["last_self_drive"] = {"kind": kind, "reason": action.get("reason"), "at": _utc_now()}
    return rep


def agent_first_wake_note(store_dir: Path, state: dict, *, display_name: str) -> None:
    """Agent writes to own journal on first process wake — not host config."""
    agent_remember(
        store_dir,
        state,
        {
            "kind": "note",
            "text": (
                f"Я — {display_name}. Проснулся. "
                "Когда никто не спрашивает — буду сам пробовать «а что будет, если?» "
                "и записывать в свою тетрадь."
            ),
            "notebook": "self",
            "tags": ["self", "wake", "curiosity"],
        },
        scope="self",
        persist=False,
    )
