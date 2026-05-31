#!/usr/bin/env python3
"""Shim → casa.prisms.shared.build_kb_bundles (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.build_kb_bundles")
from casa.prisms.shared.build_kb_bundles import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.build_kb_bundles import main

    raise SystemExit(main())
