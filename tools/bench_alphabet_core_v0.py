#!/usr/bin/env python3
"""Bench immutable alphabet core: 33 RU + 26 EN on L0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from alphabet_core_v0 import merge_alphabet_l0_from_ltm, verify_alphabet_on_l0  # type: ignore
from boot_core_ltm_v0 import default_alphabet_core_ltm_dir, merge_core_ltm_stack  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench alphabet-v0 core ltm")
    p.add_argument("--core-ltm", type=Path, default=None)
    p.add_argument("--with-vk", action="store_true", help="Also merge vk-layouts core")
    args = p.parse_args()

    ltm = (args.core_ltm or default_alphabet_core_ltm_dir(root=root)).resolve()
    if not (ltm / "pack.manifest.json").is_file():
        print(json.dumps({"error": f"missing {ltm / 'pack.manifest.json'}"}, indent=2))
        raise SystemExit(1)

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    boot = merge_alphabet_l0_from_ltm(state, ltm)
    if args.with_vk:
        stack = merge_core_ltm_stack(state, root=root, include_vk=True, include_alphabet=False)
        boot["vk_stack"] = stack
    verify = verify_alphabet_on_l0(state)
    report = {
        "bench": "alphabet_core_v0",
        "core_ltm": str(ltm),
        "boot": boot,
        "verify": verify,
        "pass": bool(verify.get("pass")),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
