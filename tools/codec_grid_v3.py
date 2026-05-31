#!/usr/bin/env python3
"""Shim → casa.prisms.shared.codec_grid_v3 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.codec_grid_v3")
from casa.prisms.shared.codec_grid_v3 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.codec_grid_v3 import main

    raise SystemExit(main())
