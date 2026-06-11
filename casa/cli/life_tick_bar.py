#!/usr/bin/env python3
"""Single-line life tick counter for console chat (pulse macro_tick)."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from casa.body.text_tract import read_afferent_cue, read_pulse, reactor_alive


def _enable_vt_on_windows() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 4)
    except OSError:
        pass


class LifeTickBar:
    """One screen row — T counts up (1, 2, 3…) while life reactor runs."""

    def __init__(
        self,
        store: Path,
        *,
        screen_row: int,
        poll_s: float = 0.35,
        display: str = "subject",
    ) -> None:
        self._store = store
        self._display = display
        self._row = max(1, screen_row)
        self._poll_s = poll_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._print_lock = threading.Lock()
        self._seen_outbox: set[str] = set()

    @staticmethod
    def _tick_value(store: Path) -> int | str:
        pulse = read_pulse(store)
        if pulse and pulse.get("macro_tick") is not None:
            return int(pulse["macro_tick"])
        return "—"

    def _line(self) -> str:
        t = self._tick_value(self._store)
        mark = "♥" if reactor_alive(self._store) else "○"
        cue = read_afferent_cue(self._store)
        busy = cue is not None and str(cue.get("status") or "") == "pending"
        suffix = " · …" if busy else ""
        return f"  life {mark} {t}{suffix}"

    def _paint(self) -> None:
        if not sys.stdout.isatty():
            return
        with self._print_lock:
            text = self._line()
            r = self._row
            sys.stdout.write(f"\033[s\033[{r};1H\r{text}\033[K\033[u")
            sys.stdout.flush()

    def bump_life_tick(self, _life_t: int | None = None, _pulse: dict | None = None) -> None:
        """Refresh bar row (callback from wait_for_efferent: life_t, pulse)."""
        self._paint()

    def note_output_lines(self, count: int = 1) -> None:
        """Shift reserved bar row down after chat printed reply lines."""
        if count > 0:
            self._row += count
            self._paint()

    def mount(self) -> None:
        _enable_vt_on_windows()
        print(self._line(), flush=True)

    def _poll_partner_outbox(self) -> None:
        from casa.domain.partner_initiative import drain_partner_outbox, peek_partner_outbox_pending

        pending = peek_partner_outbox_pending(self._store)
        new = [p for p in pending if str(p.get("id") or "") not in self._seen_outbox]
        if not new:
            return
        for row in new:
            self._seen_outbox.add(str(row.get("id") or ""))
        for row in drain_partner_outbox(self._store, limit=max(1, len(new))):
            text = str(row.get("text") or "").strip()
            if not text:
                continue
            with self._print_lock:
                if sys.stdout.isatty():
                    sys.stdout.write(f"\n{self._display}> {text}\nты> ")
                else:
                    print(f"{self._display}> {text}")
                sys.stdout.flush()

    def start(self) -> None:
        def _run() -> None:
            while not self._stop.wait(self._poll_s):
                try:
                    self._poll_partner_outbox()
                    self._paint()
                except OSError:
                    pass

        self._thread = threading.Thread(target=_run, daemon=True, name="life-tick-bar")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if sys.stdout.isatty():
            try:
                r = self._row
                sys.stdout.write(f"\033[{r};1H\r\033[K")
                sys.stdout.flush()
            except OSError:
                pass


def mount_life_tick_bar(
    store: Path,
    *,
    header_lines_before: int,
    display: str = "subject",
) -> LifeTickBar | None:
    """Reserve one row under the header; returns None if not a TTY."""
    if not sys.stdout.isatty():
        return None
    bar = LifeTickBar(store, screen_row=header_lines_before + 1, display=display)
    bar.mount()
    bar.start()
    return bar
