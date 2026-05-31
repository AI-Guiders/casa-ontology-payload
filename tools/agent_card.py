#!/usr/bin/env python3
"""Shim → casa.prisms.shared.agent_card (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.agent_card")
from casa.prisms.shared.agent_card import *  # noqa: F403
