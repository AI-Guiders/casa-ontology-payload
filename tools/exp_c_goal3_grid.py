#!/usr/bin/env python3
"""Shim → casa.cli.exp_c_goal3_grid (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_c_goal3_grid")
from casa.cli.exp_c_goal3_grid import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_c_goal3_grid import main

    raise SystemExit(main())
