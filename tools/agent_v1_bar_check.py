#!/usr/bin/env python3
"""Agent v1 existence bar — automated subset of ADR-0022 (A4, B2, C3)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.prisms.memory.kernel_memory_health import (
    C3_BAR_CHECK_IDS,
    MaintainContext,
    maintain_memory_kernel,
    run_memory_kernel_health,
)
from casa.prisms.memory.memory_prisms import ensure_prisms, hippo_episodes
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import field_state_path, ltm_root


def _check_ltm_shipped(store_dir: Path) -> dict:
    manifest = ltm_root(store_dir) / "pack.manifest.json"
    ok = manifest.is_file()
    detail: dict = {"path": str(manifest), "exists": ok}
    if ok:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        lattices = data.get("lattices") or {}
        detail["lattice_count"] = len(lattices) if isinstance(lattices, dict) else 0
        detail["field_version"] = data.get("field_version")
    return {"id": "C1_ltm_shipped", "ok": ok and detail.get("lattice_count", 0) > 0, "detail": detail}


def _check_hippo_queue(state: dict, *, cap: int) -> dict:
    n = len(hippo_episodes(state))
    return {
        "id": "B2_hippo_bounded",
        "ok": n <= cap,
        "warn": n > cap // 2,
        "detail": {"episodes": n, "cap": cap},
    }


def _check_c3_kernel_in_process(health: dict) -> dict:
    """ADR-0022 C3 — router, hippo, hot, layout, kinds (not NCA model presence)."""
    checks = [c for c in health.get("checks", []) if c.get("id") in C3_BAR_CHECK_IDS]
    failed = [c["id"] for c in checks if not c.get("ok")]
    return {
        "id": "C3_kernel_in_process",
        "ok": len(failed) == 0,
        "detail": {"checks_failed": failed, "field_version": health.get("field_version")},
    }


def _check_a4_self_repair(state: dict, store_dir: Path) -> dict:
    """ADR-0022 A4 — maintain_memory_kernel runs in-process (no external-only script)."""
    rep = maintain_memory_kernel(
        state,
        store_dir,
        repair=True,
        ctx=MaintainContext(phase="bar_check"),
    )
    status = str(rep.get("status") or "")
    ok = status in ("repaired", "noop") and isinstance(rep.get("repaired"), list)
    return {
        "id": "A4_self_repair",
        "ok": ok,
        "detail": {"status": status, "repaired_aspects": [r.get("aspect") for r in rep.get("repaired") or []]},
    }


def _check_boot_ltm(store_dir: Path, *, boot_ltm: bool) -> dict:
    fs = field_state_path(store_dir)
    if boot_ltm:
        rep = boot_store(store_dir, prefer_field_state=False)
        state = rep["state"]
        source = rep.get("source", "ltm")
    elif fs.is_file():
        from casa.prisms.shared.field_write import load_field_state

        state = ensure_prisms(load_field_state(fs, store_dir=store_dir))
        source = "field_state"
    else:
        return {
            "id": "A1_cold_boot",
            "ok": False,
            "detail": {"reason": "no_field_state_and_no_boot_ltm"},
        }
    fv = int(state.get("field_version") or 0)
    return {
        "id": "A1_cold_boot",
        "ok": fv >= 0 and "prisms" in state,
        "detail": {"source": source, "field_version": fv},
    }


def run_bar_check(
    store_dir: Path,
    *,
    boot_ltm: bool = True,
    hippo_cap: int = 512,
) -> dict:
    store_dir = store_dir.resolve()
    items = [
        _check_boot_ltm(store_dir, boot_ltm=boot_ltm),
        _check_ltm_shipped(store_dir),
    ]
    if boot_ltm:
        rep = boot_store(store_dir, prefer_field_state=not boot_ltm)
        state = rep["state"]
    else:
        fs = field_state_path(store_dir)
        from casa.prisms.shared.field_write import load_field_state

        state = ensure_prisms(load_field_state(fs, store_dir=store_dir))
    items.append(_check_hippo_queue(state, cap=hippo_cap))
    health = run_memory_kernel_health(state, store_dir=store_dir)
    items.append(_check_c3_kernel_in_process(health))
    items.append(_check_a4_self_repair(state, store_dir))
    ok = all(i["ok"] for i in items)
    return {
        "store_dir": str(store_dir),
        "ok": ok,
        "bar": "agent_v1_subset",
        "checks": items,
        "kernel_health": health,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="ADR-0022 subset bar check for agent store")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--boot-ltm", action="store_true", help="cold boot from ltm/ (A1)")
    p.add_argument("--hippo-cap", type=int, default=512)
    args = p.parse_args()
    out = run_bar_check(args.store_dir, boot_ltm=args.boot_ltm, hippo_cap=args.hippo_cap)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
