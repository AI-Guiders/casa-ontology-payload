#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_concept_locality (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_concept_locality")
from casa.cli.bench.bench_concept_locality import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_concept_locality import main

    raise SystemExit(main())
