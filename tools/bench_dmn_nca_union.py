#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_dmn_nca_union (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_dmn_nca_union")
from casa.cli.bench.bench_dmn_nca_union import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_dmn_nca_union import main

    raise SystemExit(main())
