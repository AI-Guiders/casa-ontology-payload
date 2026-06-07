#!/usr/bin/env python3
"""Von-neumann store: consistency oracle + optional repair (step 1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.boot_repair_scheduler import repair_pending, run_consistency_repair_on_sleep
from casa.domain.consistency_oracle import (
    apply_repair_homeostasis,
    assess_field_consistency,
    persist_consistency_note,
)
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_boot import boot_store


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--repair", action="store_true", help="Run sync_routes + NCA regrow if repair_pending")
    p.add_argument("--force-repair", action="store_true", help="Set repair_pending from mismatches then repair")
    p.add_argument("--max-nca-shards", type=int, default=8)
    p.add_argument("--device", default="cpu")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store_dir = args.store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]

    before = assess_field_consistency(store_dir, state)
    persist_consistency_note(store_dir, before)

    repair_report: dict | None = None
    if args.force_repair and before.get("repair_recommended"):
        apply_repair_homeostasis(state, before)
    if args.repair and (repair_pending(state) or args.force_repair):
        repair_report = run_consistency_repair_on_sleep(
            state,
            store_dir,
            max_nca_shards=args.max_nca_shards,
            device=args.device,
        )
        save_field_state(store_dir / "field_state.json", state)

    after = assess_field_consistency(store_dir, state)
    persist_consistency_note(store_dir, after)

    report = {
        "store": str(store_dir),
        "before": before,
        "after": after,
        "repair": repair_report,
        "ok": bool(after.get("ok")),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
