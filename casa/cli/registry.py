"""CLI module registry: short name → casa module with main()."""

from __future__ import annotations

import importlib.util
import json
import sys
from importlib import import_module
from pathlib import Path

_MODULES_PATH = Path(__file__).resolve().parent / "cli_modules.json"


def modules() -> dict[str, str]:
    return json.loads(_MODULES_PATH.read_text(encoding="utf-8"))


def import_cli_module(name: str):
    key = name.removesuffix(".py")
    mapping = modules()
    if key not in mapping:
        known = ", ".join(sorted(mapping)[:8])
        raise KeyError(f"unknown CLI module {name!r}; {len(mapping)} registered (e.g. {known}, …)")
    return import_module(mapping[key])


def main_entry(name: str) -> str:
    return modules()[name.removesuffix(".py")]
