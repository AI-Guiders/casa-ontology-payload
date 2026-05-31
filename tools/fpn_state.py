#!/usr/bin/env python3
"""Shim → casa.prisms.control.fpn_state (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.control.fpn_state")
from casa.prisms.control.fpn_state import *  # noqa: F403
