#!/usr/bin/env python3
"""CLI: recover agent store after crash-zeroed checkpoints (wraps casa.domain.store_recovery)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.store_recovery import recover_store_checkpoints
from casa.prisms.shared.store_boot import boot_store


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, default=_REPO / "agents" / "von-neumann")
    p.add_argument("--no-thin-rebuild", action="store_true")
    args = p.parse_args()

    store = args.store_dir.resolve()
    report = recover_store_checkpoints(store, persist_thin=not args.no_thin_rebuild)
    boot = boot_store(store, prefer_field_state=True)
    state = boot["state"]
    out = {
        **report,
        "field_version": state.get("field_version"),
        "store_id": (state.get("store") or {}).get("store_id"),
        "boot_source": (state.get("store") or {}).get("boot_source"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not report.get("field_db", {}).get("ok") and not report.get("recovered"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
