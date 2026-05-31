#!/usr/bin/env python3
"""Shim → casa.prisms.control.agent_sn_cen_tick (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.control.agent_sn_cen_tick")
from casa.prisms.control.agent_sn_cen_tick import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.control.agent_sn_cen_tick import main

    raise SystemExit(main())
