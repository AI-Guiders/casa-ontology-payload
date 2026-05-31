#!/usr/bin/env python3
"""Shim → casa.prisms.memory.bukvar_field (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.memory.bukvar_field")
from casa.prisms.memory.bukvar_field import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.memory.bukvar_field import main

    raise SystemExit(main())
