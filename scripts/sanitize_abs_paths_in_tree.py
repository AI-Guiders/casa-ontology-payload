#!/usr/bin/env python3
"""Replace absolute machine paths with repo-relative POSIX paths in text files."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Windows drive paths into user/workspace roots (same family as check_no_abs_paths).
LEAK_RE = re.compile(
    r"[A-Za-z]:[\\/]+(?:Users|Experiments|Windows|Program)[^\s\"']*",
    re.IGNORECASE,
)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True, check=True
    )
    return [ROOT / line for line in out.stdout.splitlines() if line]


def to_repo_rel(match: re.Match[str]) -> str:
    raw = match.group(0).replace("\\", "/")
    try:
        rel = Path(raw).resolve().relative_to(ROOT.resolve())
        return rel.as_posix()
    except ValueError:
        # Outside repo — strip to generic placeholder.
        if "agent-notes" in raw.lower():
            return "../agent-notes/knowledge"
        return "<repo>"


def sanitize_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    new = LEAK_RE.sub(to_repo_rel, text)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Sanitize absolute paths in git-tracked text files")
    p.add_argument("--paths", nargs="*", help="Optional explicit files; default = all tracked")
    args = p.parse_args()
    targets = [ROOT / x for x in args.paths] if args.paths else tracked_files()
    changed = 0
    for path in targets:
        if path.is_file() and sanitize_file(path):
            changed += 1
            print(path.relative_to(ROOT))
    print(f"updated {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
