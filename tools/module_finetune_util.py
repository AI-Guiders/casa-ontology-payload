#!/usr/bin/env python3
"""Shim → casa.prisms.shared.module_finetune_util (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.module_finetune_util")
from casa.prisms.shared.module_finetune_util import *  # noqa: F403
