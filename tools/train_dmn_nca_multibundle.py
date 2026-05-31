#!/usr/bin/env python3
"""Shim → casa.cli.train_dmn_nca_multibundle (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.train_dmn_nca_multibundle")
from casa.cli.train_dmn_nca_multibundle import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.train_dmn_nca_multibundle import main

    raise SystemExit(main())
