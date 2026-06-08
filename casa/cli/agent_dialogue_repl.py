#!/usr/bin/env python3
"""Interactive dialogue — partner mode of agent-life engine (agent_sn_cen_tick)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_mode import apply_subject_profile, is_subject_mode, subject_display_name
from casa.prisms.control.agent_sn_cen_tick import interactive_dialogue_config, run_dialogue_partner_turn
from casa.prisms.control.fpn_state import load_session, save_session
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.store_lock import store_session_lock
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
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def _print_banner(store: Path, display: str) -> None:
    turns = len(load_dialogue_turns(store))
    print()
    print(f"CASA dialogue — {display} ({store.name})")
    print("Режим partner-turn через agent_sn_cen_tick (тот же субъект, что autonomous tick).")
    print("Пиши сообщения; пустая строка или /quit — выход.")
    print("Команды: /help /turns /remember <текст> /verbose /sleep")
    if turns:
        print(f"В сессии уже {turns} реплик в dialogue ring.")
    print()


def _print_help() -> None:
    print(
        "\n".join(
            [
                "Команды:",
                "  /help              — эта справка",
                "  /quit, /exit, /q   — выход с сохранением store",
                "  /turns [N]         — последние N реплик (по умолчанию 6)",
                "  /remember <текст>  — запись в journal (observation)",
                "  /verbose           — показывать intent тракта",
                "  /sleep             — короткий sleep (consolidate на store)",
                "  /passage           — многострочный ввод до пустой строки",
            ]
        )
    )


def _read_passage(prompt: str = "... ") -> str:
    print("Многострочный ввод (пустая строка — конец):")
    lines: list[str] = []
    while True:
        try:
            chunk = input(prompt)
        except EOFError:
            break
        if not chunk.strip() and lines:
            break
        if chunk.strip() or lines:
            lines.append(chunk)
    return "\n".join(lines).strip()


def _run_sleep(store: Path, state: dict) -> str:
    from casa.prisms.hippo.sleep_replay import PRODUCTION_SLEEP_REPLAY
    from casa.prisms.memory.memory_prisms import hippo_episodes, run_sleep
    from casa.prisms.shared.store_bundles import load_store_bundles

    bundle = load_store_bundles(store)
    before = len([e for e in hippo_episodes(state) if not e.get("consolidated")])
    state.setdefault("sn", {})["mode"] = "sleep"
    report = run_sleep(
        state,
        bundle,
        stack_path=REPO_ROOT / "design/prisms/memory/stack.json",
        strength=4,
        replay_k=min(8, PRODUCTION_SLEEP_REPLAY.replay_k),
        replay_value_weight=PRODUCTION_SLEEP_REPLAY.value_weight,
    )
    merged = int((report or {}).get("merged_episodes") or (report or {}).get("episodes_merged") or 0)
    try:
        from casa.prisms.neuromodulator import neuromodulator_after_sleep, neuromodulator_is_active

        if neuromodulator_is_active(state):
            neuromodulator_after_sleep(state)
    except ImportError:
        pass
    return f"sleep ok: pending {before} → merged {merged}"


def _handle_slash(
    line: str,
    *,
    store: Path,
    state: dict,
    verbose: bool,
) -> tuple[str | None, bool, bool, bool]:
    """Returns (command_result, should_quit, verbose_new, consumed)."""
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"/quit", "/exit", "/q"}:
        return None, True, verbose, True

    if cmd == "/help":
        _print_help()
        return None, False, verbose, True

    if cmd == "/verbose":
        return ("verbose on" if not verbose else "verbose off"), False, not verbose, True

    if cmd == "/turns":
        n = 6
        if arg.isdigit():
            n = max(1, min(32, int(arg)))
        turns = load_dialogue_turns(store)[-n:]
        if not turns:
            return ("(пусто)", False, verbose, True)
        lines = []
        for t in turns:
            who = "ты" if t.speaker == "partner" else subject_display_name(state, store)
            lines.append(f"  [{t.kind}] {who}: {t.text[:240]}")
        return ("\n".join(lines), False, verbose, True)

    if cmd == "/remember":
        if not arg:
            return ("нужен текст: /remember ...", False, verbose, True)
        agent_remember(
            store,
            state,
            {"kind": "observation", "text": arg, "tags": ["repl", "partner-cue"]},
            scope="self",
        )
        return ("записал в journal.", False, verbose, True)

    if cmd == "/sleep":
        try:
            msg = _run_sleep(store, state)
        except Exception as exc:  # noqa: BLE001 — repl surface
            msg = f"sleep failed: {exc}"
        return (msg, False, verbose, True)

    if cmd == "/passage":
        text = _read_passage()
        return (text or None, False, verbose, False)

    return (f"неизвестная команда: {cmd} (/help)", False, verbose, True)


def _partner_reply(
    query: str,
    *,
    store: Path,
    state: dict,
    wm,
    verbose: bool,
) -> tuple[str, dict[str, Any], object, dict]:
    reply, report, wm_next, state = run_dialogue_partner_turn(
        store,
        user_query=query,
        wm=wm,
        state=state,
        config=interactive_dialogue_config(),
    )
    dialogue = report.get("dialogue") or {}

    if dialogue.get("forced_sleep"):
        try:
            sleep_msg = _run_sleep(store, state)
            if verbose:
                print(f"  · metabolic: {sleep_msg}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"  · metabolic sleep failed: {exc}", file=sys.stderr)

    if verbose:
        cen = report.get("cen") or {}
        metabolic = dialogue.get("metabolic_zone") or {}
        neuromod = dialogue.get("neuromodulator_zone") or {}
        print(
            f"  · intent={cen.get('intent')} tick={report.get('tick')} "
            f"atp={metabolic.get('atp_current')}",
            file=sys.stderr,
        )
        if neuromod:
            print(
                f"  · neuromod: arousal={neuromod.get('arousal_drive')} "
                f"threat={neuromod.get('threat_tone')} panic={neuromod.get('panic_risk')}",
                file=sys.stderr,
            )

    return reply, report, wm_next, state


def run_repl(
    store: Path,
    *,
    persist: bool = True,
    verbose: bool = False,
    partner_label: str = "ты",
) -> int:
    if not store.is_dir():
        print(f"store not found: {store}", file=sys.stderr)
        return 2

    _configure_stdio_utf8()

    with store_session_lock(store, holder="agent_dialogue_repl"):
        state = resolve_ingest_state(store, None)
        apply_subject_profile(store, state)
        if not is_subject_mode(state, store):
            print(
                f"store {store.name} не в subject_mode — включи subject_mode в store_profile.json",
                file=sys.stderr,
            )
            return 2

        display = subject_display_name(state, store)
        _print_banner(store, display)

        wm = load_session(store)

        try:
            while True:
                try:
                    line = input(f"{partner_label}> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not line:
                    break

                if line.startswith("/"):
                    msg, quit_now, verbose, consumed = _handle_slash(
                        line, store=store, state=state, verbose=verbose
                    )
                    if msg:
                        print(msg)
                    if consumed:
                        if quit_now:
                            break
                        if persist:
                            mark_runtime_dirty(state)
                            save_runtime_state(store, state, force=True, sync_ltm_on_save=False)
                        continue
                    if not msg and quit_now:
                        break
                    line = msg or ""
                    if not line:
                        continue

                reply, _report, wm, state = _partner_reply(
                    line,
                    store=store,
                    state=state,
                    wm=wm,
                    verbose=verbose,
                )
                print(f"{display}> {reply}")
                print()

                if persist:
                    save_session(store, wm)
                    mark_runtime_dirty(state)
                    save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

        finally:
            if persist:
                save_session(store, wm)
                mark_runtime_dirty(state)
                save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

    print("Пока.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann", help="store id under agents/ or path")
    p.add_argument("--partner-label", default="ты", help="prompt label for your lines")
    p.add_argument("--no-persist", action="store_true", help="do not write store on exit")
    p.add_argument("--verbose", action="store_true", help="show tract intent on stderr")
    args = p.parse_args()
    raise SystemExit(
        run_repl(
            _store_dir(args.store),
            persist=not args.no_persist,
            verbose=args.verbose,
            partner_label=args.partner_label,
        )
    )


if __name__ == "__main__":
    main()
