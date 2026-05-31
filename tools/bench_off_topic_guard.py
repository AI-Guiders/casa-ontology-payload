#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_off_topic_guard (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_off_topic_guard")
from casa.cli.bench.bench_off_topic_guard import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_off_topic_guard import main

    raise SystemExit(main())
