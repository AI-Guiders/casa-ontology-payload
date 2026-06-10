#!/usr/bin/env python3
"""Partner initiative — outbox + defer_scheduled follow-up (partnership design §2, P22b)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

InitiativeKind = Literal[
    "partner_ping",
    "defer_scheduled",
    "journal_reflect",
    "clarify_probe",
    "idle_initiate",
]

_OUTBOX_NAME = "partner_outbox.jsonl"
_BODY_TEXT_DIR = Path("body") / "text"
_OPEN_THREAD_KEY = "open_partner_thread"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text_dir(store_dir: Path, *, create: bool = False) -> Path:
    path = store_dir.resolve() / _BODY_TEXT_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def outbox_path(store_dir: Path) -> Path:
    return _text_dir(store_dir) / _OUTBOX_NAME


def _atomic_append_line(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


_PARTNER_DIALOGUE_GOAL_PREFIXES = ("goal.dialog.",)


def _wm_on_partner_line(wm: Any | None) -> bool:
    if wm is None:
        return False
    gid = str(getattr(wm, "goal_id", "") or "").strip().lower()
    return any(gid.startswith(p) for p in _PARTNER_DIALOGUE_GOAL_PREFIXES)


def subject_busy_for_partner(
    state: dict[str, Any],
    store_dir: Path | None,
    wm: Any | None = None,
) -> bool:
    """Own line / practice active — boundary greeting_while_busy applies only then.

    Partner chat (goal.dialog.*) is not «busy with own practice» — answering is the line.
    """
    if wm is None and store_dir is not None:
        from casa.prisms.control.fpn_state import load_session

        wm = load_session(store_dir)
    if _wm_on_partner_line(wm):
        return False
    if wm is not None:
        gid = str(getattr(wm, "goal_id", "") or "").strip()
        if gid and not gid.startswith("goal.dialog."):
            return True
        goal = str(getattr(wm, "goal", "") or "").strip()
        if goal and not goal.startswith("dialog:"):
            weak = state.get("last_weakest_link") if isinstance(state.get("last_weakest_link"), dict) else {}
            if weak.get("concept_id") and goal.startswith("practice:"):
                return True
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    if meta.get("self_drive_active"):
        return True
    agent = state.get("agent") if isinstance(state.get("agent"), dict) else {}
    if agent.get("own_line_active"):
        return True
    field = state.get("field") if isinstance(state.get("field"), dict) else {}
    practice = field.get("deliberate_practice") if isinstance(field.get("deliberate_practice"), dict) else {}
    if practice.get("active"):
        return True
    arbiter = state.get("goal_arbiter") if isinstance(state.get("goal_arbiter"), dict) else {}
    load = arbiter.get("load") if isinstance(arbiter.get("load"), dict) else {}
    if load.get("overloaded"):
        return True
    disp = arbiter.get("subject_disposition")
    if isinstance(disp, dict):
        reason = str(disp.get("reason") or "")
        if reason in ("own_practice_first", "cognitive_overload", "defense_sublimation"):
            return True
    return False


def record_defer_open_thread(
    state: dict[str, Any],
    *,
    partner_text: str,
    reason: str,
    tick: int,
) -> None:
    """Remember partner turn deferred — flush when gate opens (defer_scheduled)."""
    meta = state.setdefault("meta", {})
    meta[_OPEN_THREAD_KEY] = {
        "partner_text": (partner_text or "").strip(),
        "reason": reason,
        "deferred_at_tick": int(tick),
        "updated_at": _utc_now(),
    }


def clear_open_partner_thread(state: dict[str, Any]) -> None:
    meta = state.get("meta")
    if isinstance(meta, dict):
        meta.pop(_OPEN_THREAD_KEY, None)


def open_partner_thread(state: dict[str, Any]) -> dict[str, Any] | None:
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    row = meta.get(_OPEN_THREAD_KEY)
    return row if isinstance(row, dict) and row.get("partner_text") else None


def enqueue_partner_outbox(
    store_dir: Path,
    text: str,
    *,
    kind: InitiativeKind,
    provenance: dict[str, Any] | None = None,
    tick: int | None = None,
) -> str:
    """Partner-visible initiative — host peripheral drains and prints."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty partner outbox text")
    entry_id = uuid.uuid4().hex[:12]
    payload: dict[str, Any] = {
        "id": entry_id,
        "text": text,
        "kind": kind,
        "status": "pending",
        "enqueued_at": _utc_now(),
        "provenance": provenance or {},
    }
    if tick is not None:
        payload["tick"] = int(tick)
    _atomic_append_line(_text_dir(store_dir, create=True) / _OUTBOX_NAME, payload)
    return entry_id


def _read_outbox_entries(store_dir: Path) -> list[dict[str, Any]]:
    path = outbox_path(store_dir)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _rewrite_outbox(store_dir: Path, entries: list[dict[str, Any]]) -> None:
    path = _text_dir(store_dir, create=True) / _OUTBOX_NAME
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in entries)
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)


def drain_partner_outbox(store_dir: Path, *, wire: str = "console", limit: int = 8) -> list[dict[str, Any]]:
    """Host peripheral: pending partner lines → mark delivered."""
    entries = _read_outbox_entries(store_dir)
    if not entries:
        return []
    now = _utc_now()
    out: list[dict[str, Any]] = []
    n = 0
    updated: list[dict[str, Any]] = []
    cap = max(1, limit)
    for row in entries:
        if str(row.get("status") or "pending") == "pending" and n < cap:
            delivered = {**row, "status": "delivered", "delivered_at": now, "wire": wire}
            out.append(delivered)
            updated.append(delivered)
            n += 1
        else:
            updated.append(row)
    if out:
        _rewrite_outbox(store_dir, updated)
    return out


def peek_partner_outbox_pending(store_dir: Path) -> list[dict[str, Any]]:
    return [e for e in _read_outbox_entries(store_dir) if str(e.get("status") or "pending") == "pending"]


def eval_defer_scheduled_partner_ping(
    store_dir: Path,
    state: dict[str, Any],
    wm: Any,
    *,
    display: str,
) -> str | None:
    """When defer gate opens — construct partner follow-up (not pack paste)."""
    thread = open_partner_thread(state)
    if not thread:
        return None
    if subject_busy_for_partner(state, store_dir, wm):
        return None
    partner_q = str(thread.get("partner_text") or "").strip()
    if not partner_q:
        clear_open_partner_thread(state)
        return None
    from casa.domain.subject_voice import compose_subject_partner_reply_with_ctx

    _ctx, text = compose_subject_partner_reply_with_ctx(
        partner_q,
        None,
        state,
        wm,
        store_dir=store_dir,
    )
    text = (text or "").strip()
    if not text:
        return None
    clear_open_partner_thread(state)
    return text


def maybe_enqueue_idle_partner_initiative(
    store_dir: Path,
    state: dict[str, Any],
    wm: Any,
    *,
    display: str,
    outbound_turns: list[dict[str, Any]],
    tick: int,
) -> list[str]:
    """Flush partner-visible idle initiative to outbox; return entry ids."""
    from casa.domain.boundary_compose import reply_has_internal_leak

    ids: list[str] = []
    thread = open_partner_thread(state)
    if thread and not subject_busy_for_partner(state, store_dir, wm):
        ping = eval_defer_scheduled_partner_ping(store_dir, state, wm, display=display)
        if ping:
            ids.append(
                enqueue_partner_outbox(
                    store_dir,
                    ping,
                    kind="defer_scheduled",
                    tick=tick,
                    provenance={
                        "why_now": "defer_gate_open",
                        "partner_text": thread.get("partner_text"),
                        "reason": thread.get("reason"),
                    },
                )
            )
            return ids

    for turn in outbound_turns:
        text = str(turn.get("text") or "").strip()
        if not text or reply_has_internal_leak(text):
            continue
        prov = turn.get("provenance") if isinstance(turn.get("provenance"), dict) else {}
        source = str(prov.get("source") or turn.get("kind") or "idle_initiate")
        kind: InitiativeKind = "idle_initiate"
        if source == "defer_scheduled":
            kind = "defer_scheduled"
        elif source in ("self_drive", "autonomy_seed", "overload", "after_sleep_retro"):
            continue
        ids.append(
            enqueue_partner_outbox(
                store_dir,
                text,
                kind=kind,
                tick=tick,
                provenance={"why_now": source, **prov},
            )
        )
    return ids
