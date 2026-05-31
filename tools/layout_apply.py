#!/usr/bin/env python3
"""Shim → casa.prisms.shared.layout_apply (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.layout_apply")
from casa.prisms.shared.layout_apply import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.layout_apply import main

    raise SystemExit(main())
