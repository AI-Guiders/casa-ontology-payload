#!/usr/bin/env python3
"""Shim → casa.prisms.shared.kb_sync (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.kb_sync")
from casa.prisms.shared.kb_sync import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.kb_sync import main

    raise SystemExit(main())
