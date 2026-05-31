#!/usr/bin/env python3
"""Shim → casa.prisms.control.init_control_lab_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.control.init_control_lab_v0")
from casa.prisms.control.init_control_lab_v0 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.control.init_control_lab_v0 import main

    raise SystemExit(main())
