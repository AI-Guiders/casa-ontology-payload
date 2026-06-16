#!/usr/bin/env python3

"""Reactive multi-turn agent session with Neumann — duplex wire + impulse summary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

STORE = "von-neumann"
DEMO_TURNS = [
    "Привет!",
    "Слушай: когда я спрашиваю «как ты», я хочу услышать про твоё состояние здесь и сейчас, не заготовку.",
    "Как ты?",
    "А про переживания — ты как? Не знаешь, совпадает ли твой опыт с человеческим?",
    "Хорошо, я тоже не знаю, но он не обязан совпадать",
    "А что ты думаешь про это?",
    "Ну вот, заходишь каждый раз, проверяешь, спит или нет.",
]


def _run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(PY), "-m", "casa.cli", "partner_agent_wire", "--store", STORE, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
        env=merged,
    )


def ensure_duplex() -> bool:
    proc = _run(["ensure"])
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout).strip(), file=sys.stderr)
        return False
    print(proc.stdout.strip())
    return True


def _turn_kind(text: str) -> tuple[str, str, str]:
    raw = (text or "").strip()
    for command, kind in (
        ("/recast ", "recast"),
        ("/expand ", "expand"),
        ("/clarify ", "clarify"),
        ("/correction ", "correction"),
    ):
        if raw.lower().startswith(command):
            return raw[len(command) :].strip(), kind, kind
    return raw, "chat", ""


def send(text: str, *, timeout: int, no_spawn: bool) -> dict:
    payload, kind, correction_kind = _turn_kind(text)
    if not payload:
        return {"error": "empty developmental turn", "text": ""}
    args = ["send", payload, "--kind", kind, "--timeout", str(timeout)]
    if correction_kind:
        args.extend(["--correction-kind", correction_kind])
    if no_spawn:
        args.append("--no-spawn")
    proc = _run(args, env={"CASA_IMPULSE_TRACE": "summary"})
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout).strip(), "text": ""}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout.strip(), "text": proc.stdout.strip()}


def recv(*, no_spawn: bool) -> list[dict]:
    args = ["recv", "--mark-read"]
    if no_spawn:
        args.append("--no-spawn")
    proc = _run(args)
    out: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def impulse_tail(limit: int = 6) -> list[dict]:
    sys.path.insert(0, str(REPO))
    from casa.nervous.impulse import read_impulse_trace
    from casa.prisms.shared.store_layout import default_agent_store

    store = default_agent_store()
    return read_impulse_trace(store, channel="partner_dialogue", limit=limit) or []


def _stdin_turns() -> Iterable[str]:
    if sys.stdin.isatty():
        while True:
            try:
                line = input("AGENT> ")
            except EOFError:
                break
            line = line.strip()
            if not line or line.lower() in {"/q", "/quit", "quit", "exit"}:
                break
            yield line
    else:
        for line in sys.stdin:
            line = line.strip()
            if line:
                yield line


def _turns_from_args(args: argparse.Namespace) -> list[str] | Iterable[str]:
    if args.demo:
        return DEMO_TURNS
    if args.turn:
        return args.turn
    return _stdin_turns()


def _print_reply(row: dict[str, Any]) -> None:
    reply = str(row.get("text") or row.get("error") or row.get("raw") or "?")
    tick = row.get("tick")
    prov_raw = row.get("provenance")
    prov: dict[str, Any] = prov_raw if isinstance(prov_raw, dict) else {}
    print(f"NEUMANN: {reply}")

    meta: list[str] = []
    if tick is not None:
        meta.append(f"tick={tick}")
    acts = prov.get("partner_speech_acts") or []
    if acts:
        meta.append(f"acts={acts}")
    trace_raw = prov.get("bind_trace")
    trace: dict[str, Any] = trace_raw if isinstance(trace_raw, dict) else {}
    if trace.get("winner_bind_hub"):
        meta.append(f"hub={trace['winner_bind_hub']}")
    if prov.get("thread_focus"):
        meta.append(f"thread_focus={prov['thread_focus']}")
    if prov.get("discourse_affect_register"):
        meta.append(f"affect={prov['discourse_affect_register']}")
    if meta:
        print(f"  [{', '.join(meta)}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Interactive developmental commands: /recast TEXT, /expand TEXT, "
            "/clarify TEXT, /correction TEXT. These are serve-and-return metadata, "
            "not expected-answer assertions."
        ),
    )
    parser.add_argument("--demo", action="store_true", help="run the old fixed demo script explicitly")
    parser.add_argument("--turn", action="append", help="operator-provided partner turn; repeatable")
    parser.add_argument("--timeout", type=int, default=90, help="wire send timeout in seconds")
    parser.add_argument("--spawn", action="store_true", help="allow partner_agent_wire to spawn life")
    args = parser.parse_args(argv)

    print("=== AGENT ↔ NEUMANN (duplex wire + impulse) ===\n")
    if not ensure_duplex():
        return 2

    no_spawn = not args.spawn
    os.environ["CASA_IMPULSE_TRACE"] = "summary"
    sent_count = 0
    for partner in _turns_from_args(args):
        print(f"AGENT: {partner}")
        row = send(partner, timeout=args.timeout, no_spawn=no_spawn)
        _print_reply(row)
        sent_count += 1
        time.sleep(0.25)
        for msg in recv(no_spawn=no_spawn):
            if str(msg.get("direction")) == "initiative":
                print(f"NEUMANN (initiative): {msg.get('text')}")
                print(f"  [kind={msg.get('kind')}]")
        print()

    print("=== IMPULSE (partner_dialogue tail) ===")
    rows = impulse_tail(limit=max(6, sent_count))
    for row in rows[-sent_count:]:
        summary_raw = row.get("summary")
        summary: dict[str, Any] = summary_raw if isinstance(summary_raw, dict) else {}
        winners = summary.get("winners") or []
        print(f"tick={row.get('tick_id')} winners={winners} events={summary.get('event_count')}")

    print("\n=== STATUS ===")
    status_args = ["status"]
    if no_spawn:
        status_args.append("--no-spawn")
    proc = _run(status_args)
    print(proc.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
