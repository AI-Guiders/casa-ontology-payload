"""Install a casa module as the current tools shim (M2 migration)."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_ROOT), str(_ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def load_casa(casa_module: str) -> ModuleType:
    return import_module(casa_module)
