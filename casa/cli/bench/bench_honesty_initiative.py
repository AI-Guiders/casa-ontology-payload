#!/usr/bin/env python3
"""Stub bench — moral north star § honesty→initiative (partnership vs degraded TBD)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.forgetting import build_forget_honesty_report, probe_honesty_initiative
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store


def main() -> int:
    p = argparse.ArgumentParser(description="Honesty→initiative probe stub (moral north star)")
    p.add_argument("--store-dir", type=Path, required=True)
    args = p.parse_args()

    store_dir = args.store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    probe = probe_honesty_initiative(state, store_dir)
    report = build_forget_honesty_report(state, store_dir=store_dir)
    out = {
        "store": store_dir.name,
        "probe": probe,
        "gate_pass": report.get("gate_pass"),
        "contributor_lines": report.get("contributor_lines") or [],
        "note": probe.get("note"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if probe.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
