#!/usr/bin/env python3
"""Shim → casa.prisms.shared.module_masks (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.module_masks")
from casa.prisms.shared.module_masks import *  # noqa: F403
