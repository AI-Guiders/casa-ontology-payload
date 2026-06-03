"""repo + visual-curriculum на sys.path до import runner_infra / curriculum_lab."""

from __future__ import annotations

import sys
from pathlib import Path


def install(from_file: str | Path) -> tuple[Path, Path]:
    p = Path(from_file).resolve()
    if p.parent.name.startswith("micro-"):
        curriculum = p.parents[1]
    elif p.parent.name == "visual-curriculum":
        curriculum = p.parent
    elif p.parent.name == "tools":
        repo = p.parents[1]
        curriculum = repo / "lab" / "visual-curriculum"
    else:
        curriculum = p.parents[1]
    repo = curriculum.parents[1]
    for entry in (repo, curriculum):
        s = str(entry)
        if s not in sys.path:
            sys.path.insert(0, s)
    return repo, curriculum
