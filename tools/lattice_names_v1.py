#!/usr/bin/env python3
"""Shim → casa.prisms.shared.lattice_names_v1 (M2 layout)."""

from _shim_v0 import load_casa

load_casa("casa.prisms.shared.lattice_names_v1")
from casa.prisms.shared.lattice_names_v1 import *  # noqa: F403
