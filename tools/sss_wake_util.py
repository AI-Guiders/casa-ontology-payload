#!/usr/bin/env python3
"""Shim → casa.prisms.hippo.sss_wake_util (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.hippo.sss_wake_util")
from casa.prisms.hippo.sss_wake_util import *  # noqa: F403
