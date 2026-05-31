#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_exp_j_repair_answer (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_exp_j_repair_answer")
from casa.cli.bench.bench_exp_j_repair_answer import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_exp_j_repair_answer import main

    raise SystemExit(main())
