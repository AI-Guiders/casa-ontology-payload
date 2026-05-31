#!/usr/bin/env python3
"""Shim → casa.prisms.memory.sss_nca_codec_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.memory.sss_nca_codec_v0")
from casa.prisms.memory.sss_nca_codec_v0 import *  # noqa: F403
