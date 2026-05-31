#!/usr/bin/env python3
"""Bukvar surface: output from field digest only (no claim.text / CEN grep)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path

from casa.prisms.memory.bukvar_codec_v0 import decode_bukvar_layer, layer_digest
from casa.prisms.shared.field_write import decode_field_grid, load_field_state


def surface_from_field(
    field_path: Path,
    layout: dict,
    *,
    layer: str = "B0",
    min_votes: int = 1,
    prompt: str = "",
) -> dict:
    region = {
        "B0": ("dmn_b0_grapheme", "grapheme."),
        "B1": ("dmn_b1_syllable", "syllable."),
        "B2": ("dmn_b2_word", "lang.word."),
    }.get(layer, ("dmn_b0_grapheme", "grapheme."))
    region_id, prefix = region

    state = load_field_state(field_path)
    grid = state.get("grid") or {}
    layer_dec = decode_bukvar_layer(grid, layout, region_id, min_votes=min_votes)
    ranked = layer_digest(layer_dec, prefix=prefix)

    surfaces: list[str] = []
    for cid, _votes in ranked[:6]:
        tail = cid.split(".", 1)[-1]
        if prefix == "grapheme.":
            surfaces.append(tail)
        elif prefix == "syllable.":
            surfaces.append(tail)
        else:
            surfaces.append(tail.replace("_", ""))

    if layer == "B0":
        body = "".join(surfaces[:4]) if surfaces else "…"
        text = f"Surface (B0): «{body}»."
    elif layer == "B1":
        text = f"Surface (B1): {' '.join(surfaces[:3])}."
    else:
        body = ", ".join(surfaces[:2]) if surfaces else "…"
        text = f"Surface (B2): {body}."

    if prompt.strip():
        text = f"Слышал: «{prompt.strip()[:60]}». {text}"

    return {
        "layer": layer,
        "region_id": region_id,
        "surface_text": text,
        "active": [{"concept_id": c, "votes": v} for c, v in ranked[:8]],
        "field_version": state.get("field_version"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v1.json"))
    p.add_argument("--layer", choices=["B0", "B1", "B2"], default="B0")
    p.add_argument("--prompt", default="")
    p.add_argument("--min-votes", type=int, default=1)
    args = p.parse_args()

    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    out = surface_from_field(
        args.store_dir / "field_state.json",
        layout,
        layer=args.layer,
        min_votes=args.min_votes,
        prompt=args.prompt,
    )
    out["wall_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
