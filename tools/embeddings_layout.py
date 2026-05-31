#!/usr/bin/env python3
"""Shim → casa.prisms.shared.embeddings_layout (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.embeddings_layout")
from casa.prisms.shared.embeddings_layout import *  # noqa: F403
