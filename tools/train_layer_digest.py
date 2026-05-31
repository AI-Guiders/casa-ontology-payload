#!/usr/bin/env python3
"""Shim → casa.cli.train_layer_digest (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.train_layer_digest")
from casa.cli.train_layer_digest import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.train_layer_digest import main

    raise SystemExit(main())
