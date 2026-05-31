#!/usr/bin/env python3
"""Shim → casa.prisms.memory.sanitize_afanasyev_corpus_v0 (M2 layout)."""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LEGACY = "sanitize_afanasyev_corpus_v0"
_mod = import_module("casa.prisms.memory.sanitize_afanasyev_corpus_v0")
sys.modules[_LEGACY] = _mod
if __name__ != "__main__":
    sys.modules[__name__] = _mod

if __name__ == "__main__":
    raise SystemExit(_mod.main())
