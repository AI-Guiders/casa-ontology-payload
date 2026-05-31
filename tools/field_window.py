#!/usr/bin/env python3
"""Shim → casa.prisms.shared.field_window (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.field_window")
from casa.prisms.shared.field_window import *  # noqa: F403
