#!/usr/bin/env python3
"""Shim → casa.prisms.shared.rebuild_agent_store (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.rebuild_agent_store")
from casa.prisms.shared.rebuild_agent_store import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.rebuild_agent_store import main

    raise SystemExit(main())
