#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_window_batch_sweep (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_window_batch_sweep")
from casa.cli.bench.bench_window_batch_sweep import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_window_batch_sweep import main

    raise SystemExit(main())
