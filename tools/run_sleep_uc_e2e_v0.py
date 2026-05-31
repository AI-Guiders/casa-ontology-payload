#!/usr/bin/env python3
"""Shim → casa.prisms.hippo.run_sleep_uc_e2e_v0 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.hippo.run_sleep_uc_e2e_v0")
from casa.prisms.hippo.run_sleep_uc_e2e_v0 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.hippo.run_sleep_uc_e2e_v0 import main

    raise SystemExit(main())
