#!/usr/bin/env python3
"""Shim → casa.prisms.shared.import_ltm_pack_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.import_ltm_pack_v0")
from casa.prisms.shared.import_ltm_pack_v0 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.import_ltm_pack_v0 import main

    raise SystemExit(main())
