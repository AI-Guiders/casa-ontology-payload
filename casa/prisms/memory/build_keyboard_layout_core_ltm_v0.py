#!/usr/bin/env python3
"""Export immutable keyboard core (physical + QWERTY + JCUKEN + punct) + optional NCA."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.import_ltm_pack_v0 import import_pack
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.vk_layout_field_v0 import VK_CORE_LATTICE_IDS
from casa.prisms.memory.keyboard_layout_core_v0 import export_keyboard_layout_core_ltm


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Export immutable keyboard layout core ltm")
    p.add_argument("--core-out", type=Path, default=root / "lab/agent-core/vk-layouts-v0")
    p.add_argument("--train-nca", action="store_true")
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--device", default="cuda")
    args = p.parse_args()

    core = args.core_out.resolve()
    manifest = export_keyboard_layout_core_ltm(core)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    import_pack(state, core / "ltm", manifest=manifest)
    save_field_state(core / "field_state.json", state, compact=True)

    out: dict = {"core_out": str(core), "totals": manifest.get("totals"), "verify": manifest.get("imprint", {}).get("verify")}
    if args.train_nca:
        nca: dict[str, str] = {}
        for lid in VK_CORE_LATTICE_IDS:
            cmd = [
                sys.executable,
                str(root / "tools/train_sss_nca_v0.py"),
                "--store-dir",
                str(core),
                "--lattice-id",
                lid,
                "--device",
                args.device,
                "--epochs",
                str(args.epochs),
                "--save-model",
            ]
            subprocess.run(cmd, check=True, cwd=str(root))
            nca[lid] = str(core / f"nca/{lid}/model.pt")
        out["nca"] = nca
    print(json.dumps(out, ensure_ascii=False, indent=2))
    verify = out.get("verify") or {}
    if not verify.get("pass"):
        raise SystemExit("keyboard core verify failed")


if __name__ == "__main__":
    main()
