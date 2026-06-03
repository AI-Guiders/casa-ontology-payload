"""sys.path для скриптов в micro-literacy / micro-geom / …"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def setup_lab_paths(from_file: str | Path) -> tuple[Path, Path]:
    """Добавить repo root и lab/visual-curriculum на sys.path. Возвращает (repo, curriculum_dir)."""
    p = Path(from_file).resolve()
    curriculum = p.parent if p.parent.name == "visual-curriculum" else p.parents[1]
    repo = curriculum.parents[1]
    for entry in (repo, curriculum):
        s = str(entry)
        if s not in sys.path:
            sys.path.insert(0, s)
    os.chdir(repo)
    return repo, curriculum
