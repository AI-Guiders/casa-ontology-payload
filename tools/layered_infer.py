#!/usr/bin/env python3
"""Shim → casa.prisms.shared.layered_infer (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.layered_infer")
from casa.prisms.shared.layered_infer import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.layered_infer import main

    raise SystemExit(main())
