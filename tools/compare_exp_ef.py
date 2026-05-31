#!/usr/bin/env python3
"""Shim → casa.cli.compare_exp_ef (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.compare_exp_ef")
from casa.cli.compare_exp_ef import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.compare_exp_ef import main

    raise SystemExit(main())
