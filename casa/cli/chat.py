#!/usr/bin/env python3
"""Fast interactive console chat with the von-neumann subject.

Unlike agent_dialogue_repl, this defers the heavy full-store checkpoint to the
session boundary (state['_defer_runtime_persist']), so each turn costs only the
cognitive tick (~sub-second) instead of a ~13s per-turn gzip of the whole field.
By default it runs in "conversation mode" (force_accept_external) so the subject
engages rather than deferring to its own practice; pass --agency to keep defer.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_mode import apply_subject_profile, is_subject_mode, subject_display_name
from casa.prisms.control.agent_sn_cen_tick import run_dialogue_partner_turn
from casa.prisms.control.fpn_state import load_session, save_session
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.orchestrator import LearningTickConfig


def _fast_chat_config() -> LearningTickConfig:
    """Dialogue-only tick: skip the autonomous learning loop (predict/retain/self-drive)
    that costs ~3s/turn and is not needed to produce a reply. Compose is unaffected."""
    return LearningTickConfig(
        act_rollout=False,
        surprise_episode=False,
        remember_on_surprise=False,
        retain_on_verified_predict=False,
        sleep_every=0,
        agent_self_drive=False,
        goal_from_surprise=False,
        kolb_relink_on_surprise=False,
        metacog_gate=False,
        spacing_on_wake=False,
        tick_log=False,
        retro_after_sleep=False,
    )


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
        "  /quit /exit /q   — выход (сохраняет опыт сессии)",
        "  /save            — сохранить опыт прямо сейчас",
        "  /turns [N]       — последние N реплик",
        "  /passage         — многострочный ввод (пассаж+вопрос), конец — пустая строка",
        "  /engage          — режим разговора (отвечать, не деферить)  [по умолчанию]",
        "  /agency          — вернуть субъектность (может деферить ради своей практики)",
        "  /help            — эта справка",
    ]
)


def _save(store: Path, state: dict, wm, *, quiet: bool = False) -> None:
    if not quiet:
        print("  …сохраняю опыт сессии (это разовая операция)…", flush=True)
    save_session(store, wm)
    mark_runtime_dirty(state)
    save_runtime_state(store, state, force=True, sync_ltm_on_save=False)


def run_chat(
    store: Path,
    *,
    engage: bool = True,
    no_save: bool = False,
    checkpoint: bool = False,
    verbose: bool = False,
) -> int:
    if not store.is_dir():
        print(f"store не найден: {store}", file=sys.stderr)
        return 2

    _configure_stdio_utf8()

    with store_session_lock(store, holder="chat"):
        state = resolve_ingest_state(store, None)
        apply_subject_profile(store, state)
        if not is_subject_mode(state, store):
            print(
                f"store {store.name} не в subject_mode — включи subject_mode в store_profile.json",
                file=sys.stderr,
            )
            return 2

        # Fast path: defer the heavy per-turn full-store checkpoint to /save and exit.
        state["_defer_runtime_persist"] = True
        if engage:
            state.setdefault("subject", {})["force_accept_external"] = True

        display = subject_display_name(state, store)
        wm = load_session(store)
        turns = len(load_dialogue_turns(store))

        print()
        print(f"CASA chat — {display} ({store.name})")
        print(f"Режим: {'разговор (engage)' if engage else 'субъектность (agency)'} · быстрые ответы · /help · /quit")
        if turns:
            print(f"В сессии уже {turns} реплик.")
        print()

        cfg = _fast_chat_config()
        dirty = False
        try:
            while True:
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
                        # fall through to run the turn with the multi-line query
                    elif cmd in ("quit", "exit", "q"):
                        break
                    elif cmd == "help":
                        print(_HELP)
                        continue
                    elif cmd == "save":
                        _save(store, state, wm)
                        dirty = False
                        continue
                    elif cmd == "engage":
                        state.setdefault("subject", {})["force_accept_external"] = True
                        print("  · режим разговора включён")
                        continue
                    elif cmd == "agency":
                        state.setdefault("subject", {}).pop("force_accept_external", None)
                        print("  · субъектность восстановлена (может деферить)")
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

                t0 = time.perf_counter()
                reply, report, wm, state = run_dialogue_partner_turn(
                    store, user_query=line, wm=wm, state=state, config=cfg
                )
                dt = (time.perf_counter() - t0) * 1000
                dirty = True
                print(f"{display}> {reply}")
                if verbose:
                    dlg = report.get("dialogue") or {}
                    cen = report.get("cen") or {}
                    print(
                        f"  · {dt:.0f} ms · intent={cen.get('intent')} "
                        f"· soft_miss={dlg.get('soft_miss')} · tick={report.get('tick')}",
                        file=sys.stderr,
                    )
                print()
        finally:
            if not no_save and dirty:
                # Dialogue turns persist per-turn already; on exit just flush working
                # memory (instant). The heavy full-field checkpoint is opt-in.
                save_session(store, wm)
                if checkpoint:
                    _save(store, state, wm)
                else:
                    print("  · диалог сохранён (полный чекпойнт поля — /save или --checkpoint)")

    print("Пока.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Fast console chat with the von-neumann subject")
    p.add_argument("--store", default="von-neumann", help="store id under agents/ or a path")
    p.add_argument("--agency", action="store_true", help="keep subject agency (may defer); default is conversation mode")
    p.add_argument("--no-save", action="store_true", help="do not persist anything on exit")
    p.add_argument("--checkpoint", action="store_true", help="full field checkpoint on exit (~slow); default flushes dialogue only")
    p.add_argument("--verbose", action="store_true", help="show per-turn latency/intent on stderr")
    args = p.parse_args()
    raise SystemExit(
        run_chat(
            _store_dir(args.store),
            engage=not args.agency,
            no_save=args.no_save,
            checkpoint=args.checkpoint,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
