"""Legacy module names → casa implementations (replaces tools/ shims)."""

from __future__ import annotations

import importlib.abc
import importlib.util
import json
import sys
from importlib import import_module
from pathlib import Path

_MANIFEST_PATH = Path(__file__).resolve().parent / "cli" / "legacy_manifest.json"
_installed = False


def manifest() -> dict[str, str]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


class _LegacyLoader(importlib.abc.Loader):
    def __init__(self, legacy: str, casa_mod: str) -> None:
        self._legacy = legacy
        self._casa_mod = casa_mod

    def create_module(self, spec):  # noqa: ANN001
        return None

    def exec_module(self, module) -> None:  # noqa: ANN001
        real = import_module(self._casa_mod)
        sys.modules[self._legacy] = real
        module.__dict__.update(real.__dict__)


class _LegacyFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):  # noqa: ANN001
        casa_mod = manifest().get(fullname)
        if not casa_mod:
            return None
        return importlib.util.spec_from_loader(fullname, _LegacyLoader(fullname, casa_mod))


def install_legacy_modules(*, eager: bool = False) -> None:
    global _installed
    if _installed:
        return
    if eager:
        for legacy, casa_mod in manifest().items():
            sys.modules.setdefault(legacy, import_module(casa_mod))
    else:
        sys.meta_path.insert(0, _LegacyFinder())
    _installed = True


def resolve_legacy(name: str) -> str:
    key = name.removesuffix(".py")
    m = manifest()
    if key not in m:
        raise KeyError(f"unknown legacy module {name!r}; see casa/cli/legacy_manifest.json")
    return m[key]


def import_legacy(name: str):
    install_legacy_modules()
    key = name.removesuffix(".py")
    if key in sys.modules:
        return sys.modules[key]
    return import_module(key)
