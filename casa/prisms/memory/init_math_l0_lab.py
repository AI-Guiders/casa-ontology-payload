#!/usr/bin/env python3
"""Lab store: F0 schema-math only (no lexicon cartridge)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_layout import STORE_MATH_L0_LAB, agent_store_dir, rel_to_repo


_L0_LAB_DROP = frozenset(
    {
        "math.entity.cow",
        "math.entity.sheep",
        "math.category.livestock",
        "M:entity:cow",
        "M:entity:sheep",
        "M:category:livestock",
    }
)


def slim_math_l0_bundle(bundle: dict) -> dict:
    """Drop Exp L livestock demo from math-l0 lab hot path (sticks/emergent ops only)."""
    out = json.loads(json.dumps(bundle))
    out["math_tokens"] = [t for t in out.get("math_tokens") or [] if t.get("token") not in _L0_LAB_DROP]
    out["claims"] = [c for c in out.get("claims") or [] if c.get("concept_id") not in _L0_LAB_DROP]
    edges = []
    for e in (out.get("graph") or {}).get("edges") or []:
        if e.get("src") in _L0_LAB_DROP or e.get("dst") in _L0_LAB_DROP:
            continue
        edges.append(e)
    out.setdefault("graph", {})["edges"] = edges
    kw = dict(out.get("math_keywords") or {})
    for k in list(kw):
        if k in _L0_LAB_DROP:
            del kw[k]
    out["math_keywords"] = kw
    out["compose_scenarios"] = [
        s
        for s in out.get("compose_scenarios") or []
        if "cow" not in str(s.get("id") or "") and "livestock" not in str(s.get("id") or "")
    ]
    return out


def init_math_l0_lab(
    store_dir: Path,
    bundle_path: Path,
    *,
    copies: int = 5,
) -> dict[str, Any]:
    store_dir.mkdir(parents=True, exist_ok=True)
    bundles = store_dir / "bundles"
    bundles.mkdir(parents=True, exist_ok=True)
    name = bundle_path.name
    dest = bundles / name
    if bundle_path.resolve() != dest.resolve():
        shutil.copy2(bundle_path, dest)

    bundle = slim_math_l0_bundle(json.loads(dest.read_text(encoding="utf-8")))
    dest.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["subsystem"] = "first_signal_math"
    state.setdefault("bundles", {})[name] = {
        "concept_count": len({c.get("concept_id") for c in bundle.get("claims") or [] if c.get("concept_id")}),
        "claim_count": len(bundle.get("claims") or []),
        "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
    }

    rep = ingest_math_bundle(state, bundle, copies=copies)
    save_field_state(store_dir / "field_state.json", state, compact=True)

    ltm = store_dir / "ltm"
    manifest = export_pack(state, ltm, lattice_ids=[SCHEMA_MATH])

    mem = store_dir / "MEMORY.md"
    rel_bundle = rel_to_repo(bundle_path) or bundle_path.as_posix()
    mem.write_text(
        "\n".join(
            [
                f"# {store_dir.name}",
                "",
                "F0 math lab — `schema-math` only (sticks, emergent ops, Exp L). **No** DetCorpus lexicon.",
                "",
                "Init:",
                "```bash",
                f"python -m casa.cli init_math_l0_lab --bundle {rel_bundle}",
                "python -m casa.cli bench_math_schema --store-dir "
                + f"lab/agent-stores/{STORE_MATH_L0_LAB}",
                "python -m casa.cli bench_schema_predict --store-dir "
                + f"lab/agent-stores/{STORE_MATH_L0_LAB} --bundle {rel_bundle}",
                "```",
                "",
                "Do **not** run stick/emergent teacher loops on `sss-ru-general` (prod RU lexicon).",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {"store_dir": str(store_dir), "ingest": rep, "ltm_totals": manifest.get("totals")}


def main() -> None:
    p = argparse.ArgumentParser(description="Init math-l0-lab (F0 schema-math only)")
    p.add_argument(
        "--store-dir",
        type=Path,
        default=agent_store_dir(STORE_MATH_L0_LAB, root=REPO_ROOT),
    )
    p.add_argument(
        "--bundle",
        type=Path,
        default=REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json",
    )
    p.add_argument("--copies", type=int, default=5)
    args = p.parse_args()
    print(json.dumps(init_math_l0_lab(args.store_dir, args.bundle, copies=args.copies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
