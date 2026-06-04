#!/usr/bin/env python3
"""S1b: build JPEGs (manual) → ingest pure compare → probe."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_BUILD = _ROOT / "lessons/visual-cards/tools/build_card_images.py"
_INGEST = _ROOT / "lab/visual-curriculum/micro-nline/run_nline_compare_pure_micro.py"
_PROBE = _ROOT / "lab/visual-curriculum/probe_nline_compare_pure_quiz.py"


def main() -> None:
    for label, script in (
        ("build", _BUILD),
        ("ingest", _INGEST),
        ("probe", _PROBE),
    ):
        print({"run": label, "script": str(script.relative_to(_ROOT))}, flush=True)
        subprocess.run([sys.executable, str(script)], cwd=_ROOT, check=True)
    print({"done": "S1b-compare-pure-chain"}, flush=True)


if __name__ == "__main__":
    main()
