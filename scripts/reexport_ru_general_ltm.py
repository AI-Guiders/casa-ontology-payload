#!/usr/bin/env python3
"""Re-export lexicon-ru-general ltm/ with canonical paths + legacy mirrors (M3/M4)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STORE = ROOT / "lab" / "agent-stores" / "lexicon-ru-general"


def main() -> int:
    if not (STORE / "field_state.json").is_file():
        print(f"missing field_state: {STORE}", file=sys.stderr)
        return 1
    from casa.prisms.shared.export_ltm_pack import export_pack
    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.memory.memory_prisms import ensure_prisms

    state = ensure_prisms(load_field_state(STORE / "field_state.json"))
    manifest = export_pack(state, STORE / "ltm", store_dir=STORE, lattice_ids=None)
    print(json.dumps(manifest.get("totals") or {}, indent=2))
    print("prism_layout_version:", manifest.get("prism_layout_version"))

    subprocess.run(
        [sys.executable, "-m", "casa.cli", "memory_manifest", "--store-dir", str(STORE), "--write"],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "casa.cli",
            "store_boot",
            "--store-dir",
            str(STORE),
            "--smoke",
            "--sample-lattice",
            "lexicon-ru-00",
        ],
        cwd=str(ROOT),
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
