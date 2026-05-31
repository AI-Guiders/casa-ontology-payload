#!/usr/bin/env python3
"""Shim → casa.cli.train_layer_gate (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.train_layer_gate")
from casa.cli.train_layer_gate import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.train_layer_gate import main

    raise SystemExit(main())
