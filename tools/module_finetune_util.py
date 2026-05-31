#!/usr/bin/env python3
"""Shim → casa.prisms.shared.module_finetune_util (M2 layout)."""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LEGACY = "module_finetune_util"
_mod = import_module("casa.prisms.shared.module_finetune_util")
sys.modules[_LEGACY] = _mod
if __name__ != "__main__":
    sys.modules[__name__] = _mod
