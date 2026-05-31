#!/usr/bin/env python3
"""Shim → casa.cli.demo_goal3_repair (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.demo_goal3_repair")
from casa.cli.demo_goal3_repair import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.demo_goal3_repair import main

    raise SystemExit(main())
