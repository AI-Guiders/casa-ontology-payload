#!/usr/bin/env python3
"""Load human-edited config: TOML preferred, JSON legacy fallback."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
import tomllib
from pathlib import Path
from typing import Any

CONFIG_SUFFIXES = (".toml", ".json")


def resolve_config_path(path: Path | str) -> Path:
    """Resolve config path; sibling .toml wins over .json when both exist."""
    p = Path(path)
    stem = p.with_suffix("") if p.suffix in CONFIG_SUFFIXES else p
    toml = stem.with_suffix(".toml")
    js = stem.with_suffix(".json")
    if toml.is_file():
        return toml
    if p.is_file():
        return p
    if js.is_file():
        return js
    return p


def load_config(path: Path | str) -> dict[str, Any]:
    p = resolve_config_path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".toml":
        return tomllib.loads(text)
    return json.loads(text)


def dump_json(data: Any, path: Path, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
