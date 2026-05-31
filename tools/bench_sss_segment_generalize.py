#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_sss_segment_generalize (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_sss_segment_generalize")
from casa.cli.bench.bench_sss_segment_generalize import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_sss_segment_generalize import main

    raise SystemExit(main())
