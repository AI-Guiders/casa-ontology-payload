#!/usr/bin/env python3
"""Shim → casa.prisms.shared.layered_nca_core (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.layered_nca_core")
from casa.prisms.shared.layered_nca_core import *  # noqa: F403
