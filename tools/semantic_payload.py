#!/usr/bin/env python3
"""Shim → casa.prisms.shared.semantic_payload (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.semantic_payload")
from casa.prisms.shared.semantic_payload import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.semantic_payload import main

    raise SystemExit(main())
