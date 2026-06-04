#!/usr/bin/env python3
"""S6: rebuild circle compare JPEGs → ingest → probe; reinforce less if ambiguous."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_BUILD = _ROOT / "lessons/visual-cards/tools/build_card_images.py"
_INGEST = _ROOT / "lab/visual-curriculum/micro-geom/run_meta_compare_circles_pure.py"
_PROBE = _ROOT / "lab/visual-curriculum/probe_meta_compare_circles_quiz.py"
_REINFORCE = _ROOT / "lab/visual-curriculum/micro-geom/reinforce_geom_circles_less_lex.py"
_REPORT = _ROOT / "lab/visual-curriculum/generated/teacher-meta-compare-circles-quiz.json"


def _probe_ambiguous() -> bool:
    if not _REPORT.is_file():
        return False
    data = json.loads(_REPORT.read_text(encoding="utf-8"))
    return int(data.get("ambiguous") or 0) > 0


def main() -> None:
    for label, script in (
        ("build", _BUILD),
        ("ingest", _INGEST),
        ("probe", _PROBE),
    ):
        print({"run": label}, flush=True)
        subprocess.run([sys.executable, str(script)], cwd=_ROOT, check=True)
    if _probe_ambiguous():
        print({"run": "reinforce-less"}, flush=True)
        subprocess.run([sys.executable, str(_REINFORCE)], cwd=_ROOT, check=True)
        subprocess.run([sys.executable, str(_PROBE)], cwd=_ROOT, check=True)
    print({"done": "S6-circles-chain"}, flush=True)


if __name__ == "__main__":
    main()
