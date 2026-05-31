#!/usr/bin/env python3
"""Build immutable alphabet core ltm (RU 33 + EN 26) and optional NCA train."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.memory.alphabet_core_v0 import export_alphabet_core_ltm
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.import_ltm_pack_v0 import import_pack
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Export immutable RU+EN alphabet to agent-core")
    p.add_argument(
        "--core-out",
        type=Path,
        default=root / "lab/agent-core/alphabet-v0",
    )
    p.add_argument("--copies-cyrl", type=int, default=6)
    p.add_argument("--copies-latn", type=int, default=5)
    p.add_argument("--train-nca", action="store_true", help="CUDA train L0 cyrl+latn on core pack")
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--device", default="cuda")
    args = p.parse_args()

    core = args.core_out.resolve()
    manifest = export_alphabet_core_ltm(
        core,
        copies_cyrl=args.copies_cyrl,
        copies_latn=args.copies_latn,
    )

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    import_pack(state, core / "ltm", manifest=manifest)
    fs = core / "field_state.json"
    save_field_state(fs, state, compact=True)

    out: dict = {"core_out": str(core), "totals": manifest.get("totals"), "verify": manifest.get("verify")}
    if args.train_nca:
        nca_paths: dict[str, str] = {}
        for lid in ("L0_grapheme_cyrl", "L0_grapheme_latn"):
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
            nca_paths[lid] = str(core / f"nca/{lid}/model.pt")
        out["nca"] = nca_paths

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not manifest.get("verify", {}).get("pass"):
        raise SystemExit("alphabet verify failed")


if __name__ == "__main__":
    main()
