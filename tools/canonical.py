#!/usr/bin/env python3
"""Shim → casa.prisms.shared.canonical (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.canonical")
from casa.prisms.shared.canonical import *  # noqa: F403
