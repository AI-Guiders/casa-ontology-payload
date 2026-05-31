#!/usr/bin/env python3
"""Shim → casa.prisms.tick.predict_tick_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.tick.predict_tick_v0")
from casa.prisms.tick.predict_tick_v0 import *  # noqa: F403
