#!/usr/bin/env python3
"""Deprecated — use casa.prisms.memory.memory_map."""

from __future__ import annotations

import warnings

from casa.prisms.memory.memory_map import (  # noqa: F401
    MEMORY_MAP_INVENTORY_JSON,
    MEMORY_MAP_MD,
    MEMORY_MAP_SUMMARY_JSON,
    build_manifest,
    build_memory_map,
    build_memory_map_summary,
    main as _main,
    render_memory_md,
    write_memory_map_artifacts,
)

warnings.warn(
    "casa.prisms.memory.memory_manifest is deprecated; use memory_map",
    DeprecationWarning,
    stacklevel=2,
)


def main() -> None:
    warnings.warn(
        "python -m casa.prisms.memory.memory_manifest is deprecated; use memory_map",
        DeprecationWarning,
        stacklevel=1,
    )
    _main()


if __name__ == "__main__":
    main()
