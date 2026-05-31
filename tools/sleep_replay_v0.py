#!/usr/bin/env python3
"""Shim → casa.prisms.hippo.sleep_replay_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.hippo.sleep_replay_v0")
from casa.prisms.hippo.sleep_replay_v0 import *  # noqa: F403
