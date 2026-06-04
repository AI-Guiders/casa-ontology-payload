#!/usr/bin/env python3
"""S4e → S4f → S5s → S5: последовательный ingest (отдельный sleep на кадр/этап)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = (
    "lab/visual-curriculum/micro-geom/run_meta_geom_angle_pure.py",
    "lab/visual-curriculum/micro-geom/run_meta_geom_orientation_pure.py",
    "lab/visual-curriculum/micro-geom/run_meta_geom_sweep_pure.py",
    "lab/visual-curriculum/micro-geom/run_meta_measure_width_pure.py",
)


def main() -> None:
    for rel in _SCRIPTS:
        script = _ROOT / rel
        print({"run": rel}, flush=True)
        subprocess.run([sys.executable, str(script)], cwd=_ROOT, check=True)
    print({"done": "geom-stages-1-4-chain"}, flush=True)


if __name__ == "__main__":
    main()
