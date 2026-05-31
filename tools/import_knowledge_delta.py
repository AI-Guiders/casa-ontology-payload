#!/usr/bin/env python3
"""Shim → casa.prisms.shared.import_knowledge_delta (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.import_knowledge_delta")
from casa.prisms.shared.import_knowledge_delta import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.import_knowledge_delta import main

    raise SystemExit(main())
