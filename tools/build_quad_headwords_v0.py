#!/usr/bin/env python3
"""Deprecated: use Native AOT casa-lexicon-build (apps/Casa.Lexicon.Build)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    proj = root / "apps" / "Casa.Lexicon.Build" / "Casa.Lexicon.Build.csproj"
    print("build_quad_headwords_v0.py is deprecated; running casa-lexicon-build …", file=sys.stderr)
    args = ["dotnet", "run", "--project", str(proj), "-c", "Release", "--", "quad", "--root", str(root)]
    args.extend(sys.argv[1:])
    raise SystemExit(subprocess.call(args))


if __name__ == "__main__":
    main()
