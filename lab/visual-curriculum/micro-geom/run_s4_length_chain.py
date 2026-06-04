#!/usr/bin/env python3
"""S4: последовательно math.length → meta «длина» (один persist в конце каждого runner)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = (
    _ROOT / "lab/visual-curriculum/micro-nline/run_nline_length_micro.py",
    _ROOT / "lab/visual-curriculum/micro-geom/run_meta_nline_length_pure.py",
)


def main() -> None:
    for script in _SCRIPTS:
        print({"run": str(script)}, flush=True)
        subprocess.run([sys.executable, str(script)], cwd=_ROOT, check=True)
    print({"done": "S4-length-chain"}, flush=True)


if __name__ == "__main__":
    main()
