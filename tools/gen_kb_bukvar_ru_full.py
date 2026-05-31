#!/usr/bin/env python3
"""Shim → casa.prisms.memory.gen_kb_bukvar_ru_full (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.memory.gen_kb_bukvar_ru_full")
from casa.prisms.memory.gen_kb_bukvar_ru_full import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.memory.gen_kb_bukvar_ru_full import main

    raise SystemExit(main())
