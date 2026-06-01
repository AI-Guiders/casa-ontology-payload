#!/usr/bin/env python3
"""Prism memory health — facade over kernel_memory_health (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.memory.kernel_memory_health import (
    HIPPO_EPISODE_SOFT_CAP,
    HOT_HARD_EDGE_COUNT,
    HOT_SOFT_EDGE_COUNT,
    MaintainContext,
    maintain_memory_kernel,
    run_memory_kernel_health,
)

# Re-export thresholds for docs/tests.
__all__ = [
    "HIPPO_EPISODE_SOFT_CAP",
    "HOT_HARD_EDGE_COUNT",
    "HOT_SOFT_EDGE_COUNT",
    "run_prism_memory_health",
]


def run_prism_memory_health(
    state: dict,
    *,
    auto_prune_hot: bool = False,
    auto_maintain_ltm_vocab: bool = False,
    auto_maintain: bool | None = None,
    store_dir: Path | None = None,
    hippo_cap: int = HIPPO_EPISODE_SOFT_CAP,
) -> dict[str, Any]:
    """Run kernel health checks; optional repair (hot prune, ltm layout, …)."""
    repair = auto_maintain if auto_maintain is not None else (auto_prune_hot or auto_maintain_ltm_vocab)
    return run_memory_kernel_health(
        state,
        repair=repair,
        store_dir=store_dir,
        ctx=MaintainContext(phase="health"),
        hippo_cap=hippo_cap,
    )


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    from casa.prisms.memory.memory_prisms import ensure_prisms
    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.shared.store_boot import boot_store
    from casa.prisms.shared.store_layout import field_state_path

    p = argparse.ArgumentParser(description="Prism memory health (kernel aspects)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--auto-prune-hot", action="store_true", help="repair: hot_context aspect")
    p.add_argument(
        "--auto-maintain",
        action="store_true",
        help="repair: all kernel aspects (hot, ltm_layout, …)",
    )
    p.add_argument(
        "--auto-maintain-ltm",
        action="store_true",
        help="deprecated alias for --auto-maintain",
    )
    p.add_argument("--boot-ltm", action="store_true", help="boot from ltm/ instead of field_state only")
    args = p.parse_args()

    if args.boot_ltm:
        rep = boot_store(args.store_dir, prefer_field_state=False)
        state = rep["state"]
    else:
        fs = field_state_path(args.store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms(
            {"schema_version": "multi_prism_v1", "field_version": 0}
        )

    repair = args.auto_maintain or args.auto_maintain_ltm or args.auto_prune_hot
    out = run_prism_memory_health(
        state,
        auto_maintain=repair,
        auto_prune_hot=args.auto_prune_hot,
        store_dir=args.store_dir,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
