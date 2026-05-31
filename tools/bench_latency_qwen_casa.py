#!/usr/bin/env python3
"""Shim → casa.cli.bench.bench_latency_qwen_casa (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.bench.bench_latency_qwen_casa")
from casa.cli.bench.bench_latency_qwen_casa import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.bench.bench_latency_qwen_casa import main

    raise SystemExit(main())
