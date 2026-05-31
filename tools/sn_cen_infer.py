#!/usr/bin/env python3
"""Shim → casa.prisms.control.sn_cen_infer (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.control.sn_cen_infer")
from casa.prisms.control.sn_cen_infer import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.control.sn_cen_infer import main

    raise SystemExit(main())
