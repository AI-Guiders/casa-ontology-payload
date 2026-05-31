#!/usr/bin/env python3
"""Shim → casa.prisms.shared.ci_smoke_bench (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.ci_smoke_bench")
from casa.prisms.shared.ci_smoke_bench import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.ci_smoke_bench import main

    raise SystemExit(main())
