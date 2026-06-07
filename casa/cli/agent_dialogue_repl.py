#!/usr/bin/env python3
"""Interactive console dialogue with a subject-mode agent store (ADR-0045)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_tick import process_dialogue_on_tick
from casa.domain.dialogue_turn import load_dialogue_turns
from casa.domain.subject_mode import apply_subject_profile, is_subject_mode, subject_display_name
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.tick.semantic_read import route_kb_read


def _store_dir(store_id: str) -> Path:
    p = Path(store_id)
    if p.is_dir():
        return p.resolve()
    return (REPO_ROOT / "agents" / store_id).resolve()


def _minimal_task(*, intent: str = "query") -> TaskEmit:
    return TaskEmit(
        intent=intent,
        action="answer_from_memory",
        concepts=[],
        edges=[],
        targets=[],
        query_to_dmn=None,
        confidence=0.5,
        answer_blocks=(),
        answer_text="",
    )


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
    wm: WorkingMemory,
    tick: int,
    verbose: bool,
) -> tuple[str, dict[str, Any]]:
    wm_next = WorkingMemory(tick=tick, goal_id=wm.goal_id, goal=wm.goal)
    bundle = load_store_bundles(store)
    pre = route_kb_read(query, bundle, store_dir=store, state=state)
    task = _minimal_task(intent=pre.intent or "query")
    rep = process_dialogue_on_tick(
        store,
        state,
        wm=wm,
        wm_next=wm_next,
        user_query=query,
        task=task,
        mem_prep={"goal_arbiter": {"load": {"overloaded": False}}},
    )

    reply = str(rep.get("reply_text") or "").strip()
    if not reply and rep.get("outbound"):
        last = rep["outbound"][-1]
        reply = str(last.get("text") or "").strip()
    if not reply and rep.get("disposition_verbalized"):
        reply = str(rep.get("last_outbound", {}).get("text") or "").strip()

    if verbose:
        print(f"  · intent={pre.intent} tracts={len(pre.tract_ranked or [])}", file=sys.stderr)

    return reply or "(молчит)", rep


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

        meta = read_session_meta(store)
        tick = int(meta.get("repl_tick") or 0)
        wm = WorkingMemory(tick=tick)

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

                reply, _rep = _partner_reply(
                    line,
                    store=store,
                    state=state,
                    wm=wm,
                    tick=tick,
                    verbose=verbose,
                )
                tick += 1
                wm = WorkingMemory(tick=tick, goal_id=wm.goal_id, goal=wm.goal)
                print(f"{display}> {reply}")
                print()

                if persist:
                    meta = read_session_meta(store)
                    meta["repl_tick"] = tick
                    from casa.prisms.control.fpn_state import write_session_meta

                    write_session_meta(store, meta)
                    mark_runtime_dirty(state)
                    save_runtime_state(store, state, force=True, sync_ltm_on_save=False)

        finally:
            if persist:
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
