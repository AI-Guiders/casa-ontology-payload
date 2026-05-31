#!/usr/bin/env python3
"""Shim → casa.cli.exp_d_kb_perdoc (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_d_kb_perdoc")
from casa.cli.exp_d_kb_perdoc import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_d_kb_perdoc import main

    raise SystemExit(main())
