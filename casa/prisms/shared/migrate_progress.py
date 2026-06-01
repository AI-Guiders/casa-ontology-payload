#!/usr/bin/env python3
"""Stdout progress for long migrate / remigrate / export runs."""

from __future__ import annotations

import os
import sys
import time
from typing import Callable


def resolve_parallel_workers(flag: int) -> int:
    """0 = auto (2..8 from cpu_count), 1 = sequential, N>=2 = cap at 32."""
    if flag == 1:
        return 1
    if flag >= 2:
        return min(32, flag)
    cpu = os.cpu_count() or 4
    return min(8, max(2, cpu))

ProgressFn = Callable[[str], None]

_enabled = True


def set_progress_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = enabled


def progress(msg: str) -> None:
    if _enabled:
        print(msg, file=sys.stderr, flush=True)


def progress_step(label: str, detail: str = "", *, elapsed_s: float | None = None) -> None:
    suffix = f" — {detail}" if detail else ""
    if elapsed_s is not None:
        progress(f"  [{elapsed_s:.1f}s] {label}{suffix}")
    else:
        progress(f"  {label}{suffix}")


class StepTimer:
    """Context manager: log step duration on exit."""

    def __init__(self, label: str, detail: str = "") -> None:
        self.label = label
        self.detail = detail
        self._t0 = 0.0

    def __enter__(self) -> StepTimer:
        self._t0 = time.perf_counter()
        progress_step(f"{self.label}…", self.detail)
        return self

    def __exit__(self, *_) -> None:
        progress_step(self.label, self.detail, elapsed_s=time.perf_counter() - self._t0)
