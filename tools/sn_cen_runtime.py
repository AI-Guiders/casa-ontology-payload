#!/usr/bin/env python3
"""Shim → casa.prisms.control.sn_cen_runtime (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.control.sn_cen_runtime")
from casa.prisms.control.sn_cen_runtime import *  # noqa: F403
