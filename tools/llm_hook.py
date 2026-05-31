#!/usr/bin/env python3
"""Shim → casa.prisms.shared.llm_hook (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.llm_hook")
from casa.prisms.shared.llm_hook import *  # noqa: F403
