#!/usr/bin/env python3
"""Shim → casa.cli.exp_h_dual_checkpoint_bench (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_h_dual_checkpoint_bench")
from casa.cli.exp_h_dual_checkpoint_bench import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_h_dual_checkpoint_bench import main

    raise SystemExit(main())
