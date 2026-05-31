#!/usr/bin/env python3
"""Shim → casa.cli.exp_f_modules (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_f_modules")
from casa.cli.exp_f_modules import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_f_modules import main

    raise SystemExit(main())
