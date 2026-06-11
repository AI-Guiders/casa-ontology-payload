#!/usr/bin/env python3
"""Console host wire to partner_text tract (ADR-0028 afferent/efferent + ADR-0046)."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.body.text_tract import (
    TEXT_WIRE_CONSOLE,
    enqueue_partner_cue,
    read_pulse,
    reactor_alive,
    wait_for_partner_reply,
)
from casa.cli.ingest_state import resolve_ingest_state
from casa.cli.life_daemon import ensure_life_reactor
from casa.cli.life_tick_bar import LifeTickBar, mount_life_tick_bar
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_mode import apply_subject_profile, is_subject_mode, subject_display_name
from casa.prisms.control.fpn_state import load_session
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.store_lock import store_write_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _store_dir(store_id: str) -> Path:
    p = Path(store_id)
    if p.is_dir():
        return p.resolve()
    return (REPO_ROOT / "agents" / store_id).resolve()


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


_HELP = "\n".join(
    [
        "Команды:",
        "  /quit /exit /q   — выход",
        "  /status          — полный пульс + wm.T",
        "  /remember <текст>— научить/поправить (запись в журнал)",
        "  /turns [N]       — последние N реплик",
        "  /passage         — многострочный ввод, конец — пустая строка",
        "  /genome          — паспорт генома",
        "  /help            — эта справка",
    ]
)


_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _maybe_split_passage(line: str) -> str:
    if "\n" in line:
        return line
    sents = [s.strip() for s in _SENT_SPLIT.split(line.strip()) if s.strip()]
    if len(sents) >= 2 and sents[-1].rstrip().endswith("?"):
        passage = " ".join(sents[:-1]).strip()
        question = sents[-1].strip()
        if len(passage) >= 12 and len(question) >= 4:
            return f"{passage}\n\n{question}"
    return line


def _format_pulse(store: Path) -> str:
    pulse = read_pulse(store)
    if not pulse:
        return "partner_text: нет пульса (life не запущена?)"
    alive = reactor_alive(store)
    tick = pulse.get("macro_tick")
    sn = pulse.get("sn_mode") or "?"
    updated = pulse.get("updated_at") or "?"
    tract = pulse.get("tract_id") or "partner_text"
    return f"{tract}: {'live' if alive else 'stale'} · T={tick} · sn={sn} · {updated}"


def _remember(store: Path, text: str) -> None:
    with store_write_lock(store, holder="chat_remember", timeout_s=60.0):
        state = resolve_ingest_state(store, None)
        apply_subject_profile(store, state)
        agent_remember(
            store,
            state,
            {"kind": "observation", "text": text, "tags": ["chat", "correction"]},
            scope="self",
        )
        mark_runtime_dirty(state)
        save_runtime_state(store, state, force=True, sync_ltm_on_save=False)


def run_chat(
    store: Path,
    *,
    no_daemon: bool = False,
    timeout_s: float = 120.0,
    verbose: bool = False,
    quiet: bool = False,
) -> int:
    if not store.is_dir():
        print(f"store не найден: {store}", file=sys.stderr)
        return 2

    _configure_stdio_utf8()

    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    if not is_subject_mode(state, store):
        print(
            f"store {store.name} не в subject_mode — включи subject_mode в store_profile.json",
            file=sys.stderr,
        )
        return 2

    display = subject_display_name(state, store)
    turns = len(load_dialogue_turns(store))

    if not no_daemon:
        print("  · проверяю life reactor…", file=sys.stderr, flush=True)
        if not ensure_life_reactor(store):
            print(
                "не удалось поднять life reactor — запусти вручную:\n"
                f"  python tools/agent_inbox_runner.py --store-dir {store} --inbox-dir {store / 'teacher_inbox'}",
                file=sys.stderr,
            )
            return 2

    header_lines = 0

    def _header(line: str = "") -> None:
        nonlocal header_lines
        if line:
            print(line)
        else:
            print()
        header_lines += 1

    _header()
    _header(f"CASA chat — {display} ({store.name})")
    _header("Режим: console → partner_text · строка life ♥ T · /status · /help · /quit")
    if turns:
        _header(f"В сессии уже {turns} реплик.")

    life_bar: LifeTickBar | None = None
    if not quiet:
        life_bar = mount_life_tick_bar(store, header_lines_before=header_lines, display=display)
        header_lines += 1
        _header()

    try:
        while True:
            from casa.domain.partner_initiative import drain_partner_outbox

            for row in drain_partner_outbox(store, limit=4):
                text = str(row.get("text") or "").strip()
                if text:
                    print(f"{display}> {text}")
                    print()
            try:
                line = input("ты> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue

            if line.startswith("/"):
                cmd, _, arg = line[1:].partition(" ")
                cmd = cmd.lower()
                if cmd in ("passage", "p"):
                    print("  (вставь пассаж+вопрос; строка с одной «.» или /end — отправить)")
                    buf: list[str] = []
                    while True:
                        try:
                            chunk = input("… ")
                        except (EOFError, KeyboardInterrupt):
                            break
                        if chunk.strip() in (".", "/end"):
                            break
                        buf.append(chunk)
                    line = "\n".join(buf).strip()
                    if not line:
                        continue
                elif cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "help":
                    print(_HELP)
                    continue
                elif cmd == "status":
                    wm = load_session(store)
                    print(f"  · {_format_pulse(store)} · wm.T={wm.tick}")
                    continue
                elif cmd in ("remember", "teach"):
                    if not arg.strip():
                        print("  · нужен текст: /remember <факт или правка>")
                    else:
                        _remember(store, arg.strip())
                        print("  · записал в журнал")
                    continue
                elif cmd == "genome":
                    from casa.prisms.genetic import format_genome_passport_repl

                    print(format_genome_passport_repl(state))
                    continue
                elif cmd == "turns":
                    n = int(arg) if arg.strip().isdigit() else 6
                    for t in load_dialogue_turns(store)[-max(1, min(40, n)):]:
                        who = "ты" if t.speaker == "partner" else display
                        print(f"  [{t.kind}] {who}: {t.text[:200]}")
                    continue
                else:
                    print(f"  неизвестная команда: /{cmd} (/help)")
                    continue

            if not no_daemon and not reactor_alive(store):
                print("  · reactor offline — перезапуск…", file=sys.stderr)
                if not ensure_life_reactor(store):
                    print("  · не удалось восстановить reactor", file=sys.stderr)
                    continue

            query = _maybe_split_passage(line)
            t0 = time.perf_counter()
            try:
                cue_id = enqueue_partner_cue(store, query, wire=TEXT_WIRE_CONSOLE)
            except TimeoutError:
                print("  · предыдущий ход ещё обрабатывается — подожди", file=sys.stderr)
                continue
            on_life = life_bar.bump_life_tick if life_bar is not None else None
            try:
                done = wait_for_partner_reply(
                    store,
                    cue_id,
                    timeout_s=timeout_s,
                    on_life_tick=on_life,
                )
            except TimeoutError:
                print("  · таймаут ответа — проверь /status", file=sys.stderr)
                continue
            except RuntimeError as err:
                print(f"  · ошибка tick: {err}", file=sys.stderr)
                continue

            reply = str(done.get("reply_text") or "").strip()
            dt = (time.perf_counter() - t0) * 1000
            print(f"{display}> {reply}")
            if life_bar is not None:
                life_bar.note_output_lines(2)
            if verbose:
                hint = done.get("report_hint") or {}
                print(
                    f"  · {dt:.0f} ms · tick={done.get('tick')} · sn={hint.get('sn_mode')}",
                    file=sys.stderr,
                )
            print()
    finally:
        if life_bar is not None:
            life_bar.stop()

    print("Пока.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Console chat — host wire to partner_text tract")
    p.add_argument("--store", default="von-neumann", help="store id under agents/ or a path")
    p.add_argument(
        "--no-daemon",
        action="store_true",
        help="do not spawn life reactor (must already be running)",
    )
    p.add_argument("--timeout", type=float, default=120.0, help="partner reply timeout (seconds)")
    p.add_argument("--verbose", action="store_true", help="per-turn timing on stderr")
    p.add_argument("--quiet", action="store_true", help="hide life tick bar")
    args = p.parse_args()
    raise SystemExit(
        run_chat(
            _store_dir(args.store),
            no_daemon=args.no_daemon,
            timeout_s=args.timeout,
            verbose=args.verbose,
            quiet=args.quiet,
        )
    )


if __name__ == "__main__":
    main()
