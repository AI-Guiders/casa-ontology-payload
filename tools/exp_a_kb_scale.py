#!/usr/bin/env python3
"""Shim → casa.cli.exp_a_kb_scale (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_a_kb_scale")
from casa.cli.exp_a_kb_scale import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_a_kb_scale import main

    raise SystemExit(main())
