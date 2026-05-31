#!/usr/bin/env python3
"""Backward compat: python tools/run.py store_boot_v0 --smoke … → python -m casa.cli …"""
from __future__ import annotations

import sys

from casa.cli._run import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
