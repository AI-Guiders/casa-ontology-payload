#!/usr/bin/env python3
"""Block 1 pedagogy — delegates to run_block_pedagogy (back-compat entry)."""

import _ensure_paths  # noqa: F401
from run_block_pedagogy import main

if __name__ == "__main__":
    import sys

    if "--block" not in sys.argv:
        sys.argv[1:1] = ["--block", "block-01-grapheme-cyrl"]
    main()
