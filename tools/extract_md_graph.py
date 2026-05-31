#!/usr/bin/env python3
"""Shim → casa.prisms.shared.extract_md_graph (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.extract_md_graph")
from casa.prisms.shared.extract_md_graph import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.extract_md_graph import main

    raise SystemExit(main())
