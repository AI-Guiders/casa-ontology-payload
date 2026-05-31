#!/usr/bin/env python3
"""Bench: after listen, grapheme/syllable/word layers appear in field decode."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.bukvar_codec import decode_bukvar_layer, layer_digest
from casa.prisms.shared.field_write import load_field_state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v1.json"))
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    state = load_field_state(args.store_dir / "field_state.json")
    grid = state.get("grid") or {}

    expected = {
        "B0": sorted({c["concept_id"] for c in bundle["claims"] if c["concept_id"].startswith("grapheme.")}),
        "B1": sorted({c["concept_id"] for c in bundle["claims"] if c["concept_id"].startswith("syllable.")}),
        "B2": sorted({c["concept_id"] for c in bundle["claims"] if c["concept_id"].startswith("lang.word.")}),
    }
    regions = {
        "B0": ("dmn_b0_grapheme", "grapheme."),
        "B1": ("dmn_b1_syllable", "syllable."),
        "B2": ("dmn_b2_word", "lang.word."),
    }

    results = {}
    for layer, (region_id, prefix) in regions.items():
        dec = decode_bukvar_layer(grid, layout, region_id, min_votes=1)
        got = {c for c, _ in layer_digest(dec, prefix=prefix)}
        exp = set(expected[layer])
        hit = exp <= got
        results[layer] = {
            "hit": hit,
            "expected": len(exp),
            "recovered": len(got & exp),
            "missing": sorted(exp - got),
            "extra": sorted(got - exp)[:5],
        }

    report = {
        "store": str(args.store_dir),
        "field_version": state.get("field_version"),
        "codec": (grid or {}).get("codec"),
        "layers": results,
        "all_layers_ok": all(r["hit"] for r in results.values()),
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
