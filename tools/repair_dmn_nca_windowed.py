#!/usr/bin/env python3
"""Shim → casa.cli.repair_dmn_nca_windowed (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.cli.repair_dmn_nca_windowed")
from casa.cli.repair_dmn_nca_windowed import *  # noqa: F403
