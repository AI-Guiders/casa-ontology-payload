#!/usr/bin/env python3
"""Shim → casa.prisms.shared.nca_train_util (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.nca_train_util")
from casa.prisms.shared.nca_train_util import *  # noqa: F403
