#!/usr/bin/env python3
"""Shim → casa.prisms.memory.extract_lexicon_from_store_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.memory.extract_lexicon_from_store_v0")
from casa.prisms.memory.extract_lexicon_from_store_v0 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.memory.extract_lexicon_from_store_v0 import main

    raise SystemExit(main())
