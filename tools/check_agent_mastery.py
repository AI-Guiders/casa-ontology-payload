#!/usr/bin/env python3
"""Teacher/lab: verify agent mastery from class.manifest mastery_probe (no runtime oracle)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from collections import defaultdict

from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store


def check_mastery(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
) -> dict:
    manifest = json.loads((class_dir / manifest_name).read_text(encoding="utf-8"))
    probes = list(manifest.get("mastery_probe") or [])
    thresholds = dict(manifest.get("mastery_threshold") or {})

    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    lats = memory_lattices(state)
    lat = lats.get(SCHEMA_MATH) or {}
    if not lat.get("cells"):
        return {"error": "no schema-math on field", "store_dir": str(store_dir)}

    dec = decode_f0_lattice(lat)
    rows: list[dict] = []
    by_tier: dict[str, list[bool]] = defaultdict(list)

    for row in probes:
        cue = str(row.get("cue") or "")
        expect = str(row.get("expect") or "")
        tier = str(row.get("tier") or "other")
        ranked = rank_cue_on_f0(dec, cue, bundle=None)
        top = ranked[0][0] if ranked else None
        top3 = [r[0] for r in ranked[:3]]
        ok = top == expect or expect in top3
        by_tier[tier].append(ok)
        rows.append(
            {
                "cue": cue,
                "expect": expect,
                "tier": tier,
                "top": top,
                "top3": top3,
                "pass": ok,
            }
        )

    tier_scores = {
        tier: (sum(vals) / len(vals) if vals else 0.0) for tier, vals in by_tier.items()
    }
    tier_pass = {
        tier: score >= float(thresholds.get(tier, 0.8)) for tier, score in tier_scores.items()
    }
    overall = all(tier_pass.values()) if tier_pass else False

    return {
        "store_dir": str(store_dir.resolve()),
        "class_id": manifest.get("class_id"),
        "field_version": state.get("field_version"),
        "probes": rows,
        "tier_scores": tier_scores,
        "tier_pass": tier_pass,
        "thresholds": thresholds,
        "mastery_ok": overall,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Check von-neumann arithmetic mastery (teacher verify)")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument(
        "--class-dir",
        type=Path,
        default=REPO_ROOT / "lessons/math-palochki",
    )
    args = p.parse_args()
    rep = check_mastery(args.store_dir or default_agent_store(), args.class_dir)
    out_path = args.class_dir / "last-mastery-report.json"
    out_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
