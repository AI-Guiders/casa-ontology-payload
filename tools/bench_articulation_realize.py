#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_articulation_realize (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_articulation_realize")
from casa.cli.bench.bench_articulation_realize import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_articulation_realize import main

    raise SystemExit(main())
