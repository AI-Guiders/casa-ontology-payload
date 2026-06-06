#!/usr/bin/env python3
"""Block 1 held-out grapheme gate — thin wrapper (see probe_block_held_out.py)."""

from probe_block_held_out import main

if __name__ == "__main__":
    import sys

    if "--block" not in sys.argv:
        sys.argv[1:1] = ["--block", "block-01-grapheme-cyrl"]
    main()
