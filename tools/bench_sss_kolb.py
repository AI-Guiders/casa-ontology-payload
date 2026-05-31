#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_sss_kolb (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_sss_kolb")
from casa.cli.bench.bench_sss_kolb import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_sss_kolb import main

    raise SystemExit(main())
