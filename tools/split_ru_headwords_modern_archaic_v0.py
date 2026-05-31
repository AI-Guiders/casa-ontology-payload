#!/usr/bin/env python3
"""Shim → casa.prisms.memory.split_ru_headwords_modern_archaic_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.memory.split_ru_headwords_modern_archaic_v0")
from casa.prisms.memory.split_ru_headwords_modern_archaic_v0 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.memory.split_ru_headwords_modern_archaic_v0 import main

    raise SystemExit(main())
