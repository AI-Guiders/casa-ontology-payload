#!/usr/bin/env python3
"""Duplex host peripheral: Cursor agent JSONL wire ↔ partner_text tract + life reactor."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.body.agent_wire import (
    append_agent_inbox,
    bridge_alive,
    drain_pending_outbox,
    mark_outbox_done,
    reclaim_stale_outbox,
    try_claim_bridge,
    write_bridge_pulse,
)
from casa.body.text_tract import (
    TEXT_WIRE_AGENT,
    enqueue_partner_cue,
    reactor_alive,
    wait_for_partner_reply,
)
from casa.cli.life_daemon import ensure_life_reactor
from casa.domain.partner_initiative import drain_partner_outbox


def _store_dir(store_id: str) -> Path:
    p = Path(store_id)
    if p.is_dir():
        return p.resolve()
    return (REPO_ROOT / "agents" / store_id).resolve()


def _spawn_detached_bridge(store: Path) -> subprocess.Popen[bytes] | subprocess.Popen[str]:
    cmd = [sys.executable, "-m", "casa.cli", "partner_agent_wire", "run", "--store", str(store)]
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        return subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,  # type: ignore[attr-defined]
            startupinfo=startupinfo,
        )
    return subprocess.Popen(cmd, cwd=str(REPO_ROOT))


def ensure_duplex(
    store: Path,
    *,
    spawn_bridge: bool = True,
    boot_timeout_s: float = 120.0,
) -> bool:
    if not ensure_life_reactor(store, boot_timeout_s=boot_timeout_s):
        return False
    if bridge_alive(store):
        return True
    if not spawn_bridge:
        return False
    proc = _spawn_detached_bridge(store)
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if bridge_alive(store):
            return True
        if proc.poll() is not None:
            return False
        time.sleep(0.2)
    return bridge_alive(store)


def run_bridge(
    store: Path,
    *,
    poll_s: float = 0.12,
    turn_timeout_s: float = 120.0,
) -> int:
    if not ensure_life_reactor(store, spawn=True):
        print("FAIL: life reactor not available", file=sys.stderr)
        return 2
    if not try_claim_bridge(store):
        print("FAIL: another partner_agent_wire bridge is already running", file=sys.stderr)
        return 3

    reclaim_stale_outbox(store)
    print(f"partner_agent_wire: duplex on {store.name} (life + JSONL bridge)", flush=True)
    seen_initiative: set[str] = set()

    def _pulse_heartbeat(**extra: object) -> None:
        write_bridge_pulse(store, extra={"life": reactor_alive(store), **extra})

    try:
        while True:
            _pulse_heartbeat(phase="idle")

            for delivered in drain_partner_outbox(store, wire=TEXT_WIRE_AGENT, limit=4):
                eid = str(delivered.get("id") or "")
                if eid:
                    seen_initiative.add(eid)
                append_agent_inbox(
                    store,
                    direction="initiative",
                    text=str(delivered.get("text") or ""),
                    kind=str(delivered.get("kind") or "partner_ping"),
                    provenance=delivered.get("provenance")
                    if isinstance(delivered.get("provenance"), dict)
                    else {},
                    tick=int(delivered["tick"]) if delivered.get("tick") is not None else None,
                )

            for req in drain_pending_outbox(store, limit=1):
                req_id = str(req.get("id") or "")
                text = str(req.get("text") or "").strip()
                if not req_id or not text:
                    mark_outbox_done(store, req_id, status="error")
                    continue
                try:
                    _pulse_heartbeat(phase="processing_turn", request_id=req_id)
                    kind = str(req.get("kind") or "chat")
                    cue_id = enqueue_partner_cue(store, text, kind=kind, wire=TEXT_WIRE_AGENT)
                    done = wait_for_partner_reply(
                        store,
                        cue_id,
                        timeout_s=turn_timeout_s,
                        on_life_tick=lambda _t, _p: _pulse_heartbeat(
                            phase="waiting_efferent",
                            request_id=req_id,
                            cue_id=cue_id,
                        ),
                    )
                    reply = str(done.get("reply_text") or "").strip()
                    req_provenance = req.get("provenance")
                    provenance = {
                        "cue_id": cue_id,
                        "wire": TEXT_WIRE_AGENT,
                        "partner_turn_kind": kind,
                    }
                    if isinstance(req_provenance, dict):
                        provenance.update(req_provenance)
                    append_agent_inbox(
                        store,
                        direction="reply",
                        text=reply or "(молчит)",
                        request_id=req_id,
                        tick=int(done["tick"]) if done.get("tick") is not None else None,
                        provenance=provenance,
                    )
                    mark_outbox_done(store, req_id, status="done")
                except Exception as err:  # noqa: BLE001 — bridge survives one bad turn
                    append_agent_inbox(
                        store,
                        direction="error",
                        text=repr(err),
                        request_id=req_id,
                    )
                    mark_outbox_done(store, req_id, status="error")

            time.sleep(max(0.05, poll_s))
    except KeyboardInterrupt:
        print("partner_agent_wire: stopped", flush=True)
        return 0


def cmd_ensure(store: Path, args: argparse.Namespace) -> int:
    ok = ensure_duplex(store, spawn_bridge=not args.no_spawn)
    if not ok:
        print("FAIL: duplex not ready (life reactor or bridge)", file=sys.stderr)
        return 1
    print("OK: life reactor + agent wire bridge")
    return 0


def cmd_send(store: Path, args: argparse.Namespace) -> int:
    from casa.body.agent_wire import enqueue_agent_outbox, find_inbox_reply, reclaim_stale_outbox, wait_inbox_reply
    import json

    reclaim_stale_outbox(store)
    if not ensure_duplex(store, spawn_bridge=not args.no_spawn):
        return 2
    req_id = enqueue_agent_outbox(
        store,
        args.text,
        kind=args.kind,
        provenance={"correction_kind": args.correction_kind} if args.correction_kind else None,
    )

    def _heartbeat() -> None:
        write_bridge_pulse(store, extra={"phase": "client_wait", "request_id": req_id})

    try:
        row = wait_inbox_reply(store, req_id, timeout_s=args.timeout, on_poll=_heartbeat)
    except TimeoutError as err:
        late = find_inbox_reply(store, req_id)
        if late is not None:
            row = late
        else:
            reclaim_stale_outbox(store)
            print(
                json.dumps(
                    {"direction": "error", "text": str(err), "request_id": req_id},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
    print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0 if str(row.get("direction")) == "reply" else 1


def cmd_recv(store: Path, args: argparse.Namespace) -> int:
    from casa.body.agent_wire import read_cursor, read_inbox, write_cursor
    import json

    after = args.after or read_cursor(store)
    rows = read_inbox(store, after_id=after, limit=args.limit)
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    if rows and args.mark_read:
        write_cursor(store, str(rows[-1].get("id") or ""))
    return 0


def cmd_status(store: Path, args: argparse.Namespace) -> int:
    from casa.body.agent_wire import outbox_in_flight
    from casa.body.text_tract import read_pulse
    import json

    payload = {
        "store": str(store),
        "life_reactor": reactor_alive(store),
        "agent_bridge": bridge_alive(store),
        "life_pulse": read_pulse(store),
        "outbox_in_flight": outbox_in_flight(store),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_repair(store: Path, args: argparse.Namespace) -> int:
    import json

    reclaimed = reclaim_stale_outbox(store)
    print(json.dumps({"reclaimed": reclaimed}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Duplex agent wire — JSONL ↔ partner_text + life")
    p.add_argument("--store", default="von-neumann", help="store id under agents/ or path")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run bridge loop (long-lived duplex host)")
    run_p.add_argument("--poll-ms", type=int, default=120)
    run_p.add_argument("--turn-timeout", type=float, default=120.0)

    ens = sub.add_parser("ensure", help="Ensure life reactor + bridge process")
    ens.add_argument("--no-spawn", action="store_true")

    send = sub.add_parser("send", help="Enqueue partner line; wait reply JSON on stdout")
    send.add_argument("text")
    send.add_argument(
        "--kind",
        choices=("chat", "recast", "expand", "clarify", "correction"),
        default="chat",
        help="developmental turn kind; metadata only, not a response oracle",
    )
    send.add_argument(
        "--correction-kind",
        choices=("recast", "expand", "clarify", "contrast"),
        default="",
        help="optional teacher-feedback class for correction turns",
    )
    send.add_argument("--timeout", type=float, default=120.0)
    send.add_argument("--no-spawn", action="store_true")

    recv = sub.add_parser("recv", help="Print new inbox lines (initiative + replies)")
    recv.add_argument("--after", default=None, help="inbox message id cursor")
    recv.add_argument("--limit", type=int, default=16)
    recv.add_argument("--mark-read", action="store_true")

    sub.add_parser("status", help="JSON status: reactor + bridge pulse")

    sub.add_parser("repair", help="Reclaim stale outbox processing rows")

    args = p.parse_args()
    store = _store_dir(args.store)

    if args.cmd == "run":
        return run_bridge(store, poll_s=max(0.05, args.poll_ms / 1000.0), turn_timeout_s=args.turn_timeout)
    if args.cmd == "ensure":
        return cmd_ensure(store, args)
    if args.cmd == "send":
        return cmd_send(store, args)
    if args.cmd == "recv":
        return cmd_recv(store, args)
    if args.cmd == "status":
        return cmd_status(store, args)
    if args.cmd == "repair":
        return cmd_repair(store, args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
