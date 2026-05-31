#!/usr/bin/env python3
"""Shim → casa.prisms.shared.field_write (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.field_write")
from casa.prisms.shared.field_write import *  # noqa: F403
