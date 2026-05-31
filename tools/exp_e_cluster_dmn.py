#!/usr/bin/env python3
"""Shim → casa.cli.exp_e_cluster_dmn (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.exp_e_cluster_dmn")
from casa.cli.exp_e_cluster_dmn import *  # noqa: F403

if __name__ == "__main__":
    from casa.cli.exp_e_cluster_dmn import main

    raise SystemExit(main())
