#!/usr/bin/env python3
"""Shim → casa.prisms.shared.kb_field_watcher (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.kb_field_watcher")
from casa.prisms.shared.kb_field_watcher import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.kb_field_watcher import main

    raise SystemExit(main())
