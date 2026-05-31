#!/usr/bin/env python3
"""Shim → casa.prisms.shared.prism_state_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.prism_state_v0")
from casa.prisms.shared.prism_state_v0 import *  # noqa: F403
