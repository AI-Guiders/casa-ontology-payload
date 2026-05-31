#!/usr/bin/env python3
"""Pre-publish guard: fail if any git-tracked file embeds an absolute machine path.

Catches a Windows drive path into a typical user/workspace root in tracked
manifests, reports and logs before the repo is pushed public.

    python scripts/check_no_abs_paths.py
    python scripts/check_no_abs_paths.py --scope ci

``--scope ci`` restricts to publish-critical trees (tools, tests, scripts,
prod store manifests). Full scan remains the default for local P0 cleanup.

Exit code 0 = clean, 1 = leaks found (printed as ``path:line``).
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LEAK_RE = re.compile(r"[A-Za-z]:[\\/]{1,2}(?:Users|Experiments|Windows|Program)", re.IGNORECASE)

CI_SCOPE_GLOBS = (
    "tools/**",
    "tests/**",
    "scripts/check_no_abs_paths.py",
    "design/CASA-ADR-*.md",
    "lab/agent-stores/sss-ru-general-v0/nca_train_registry.v0.json",
    "lab/agent-stores/sss-ru-general-v0/ltm/pack.manifest.json",
    "lab/agent-stores/sss-ru-general-v0/memory_manifest.json",
    "lab/agent-stores/sss-ru-lexicon-v0/nca_train_registry.v0.json",
    "lab/agent-stores/sss-en-folk-v0/nca_train_registry.v0.json",
)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line]


def in_scope(rel: str, patterns: tuple[str, ...]) -> bool:
    norm = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(norm, pat) for pat in patterns)


def main() -> int:
    p = argparse.ArgumentParser(description="Detect absolute machine paths in tracked files")
    p.add_argument(
        "--scope",
        choices=("all", "ci"),
        default="all",
        help="ci = publish-critical paths only (for CI gate)",
    )
    args = p.parse_args()
    scope_patterns = CI_SCOPE_GLOBS if args.scope == "ci" else None

    hits: list[str] = []
    for rel in tracked_files():
        if scope_patterns is not None and not in_scope(rel, scope_patterns):
            continue
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if LEAK_RE.search(line):
                hits.append(f"{rel}:{i}")

    if hits:
        print(f"Absolute machine paths in {len(hits)} tracked location(s):", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    label = "CI scope" if args.scope == "ci" else "tracked files"
    print(f"OK: no absolute machine paths in {label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
