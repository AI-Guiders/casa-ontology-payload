#!/usr/bin/env python3
"""Shim → casa.prisms.shared.build_kb_modules (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.build_kb_modules")
from casa.prisms.shared.build_kb_modules import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.build_kb_modules import main

    raise SystemExit(main())
