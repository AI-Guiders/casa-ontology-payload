#!/usr/bin/env python3
"""Shim → casa.prisms.shared.migrate_lattice_ids_v1 (M2 layout)."""
from _shim_v0 import load_casa

load_casa("casa.prisms.shared.migrate_lattice_ids_v1")
from casa.prisms.shared.migrate_lattice_ids_v1 import *  # noqa: F403

if __name__ == "__main__":
    from casa.prisms.shared.migrate_lattice_ids_v1 import main

    raise SystemExit(main())
