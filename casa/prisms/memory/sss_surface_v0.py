#!/usr/bin/env python3
"""Surface output from SSS lattice stack (no claims_nav / CEN)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_l2_shard_v0 import is_l2_word_lattice, lattice_digest_l2_network
from casa.prisms.memory.sss_stack_v0 import decode_lattice, lattice_digest, load_stack
from casa.prisms.hippo.sss_wake_util import concept_to_surface, rank_for_cue


def surface_from_sss(
    state: dict,
    *,
    lattice_id: str | None = None,
    min_votes: int = 1,
    prompt: str = "",
) -> dict:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    if not lattices:
        raise ValueError("field_state has no memory lattices")

    mem = (state.get("prisms") or {}).get("prism_memory") or {}
    sss = state.get("sss") or {}
    stack_path = mem.get("stack") or sss.get("stack") or "design/sss-lattice-stack.v0.json"
    stack = load_stack(Path(stack_path))
    lid = lattice_id or str(mem.get("active_lattice") or sss.get("active_lattice") or "L0_grapheme")
    if lid not in lattices:
        raise KeyError(lid)

    prefix = ""
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lid:
            prefix = str(lat.get("concept_prefix") or "")
            break

    decoded = decode_lattice(lattices[lid], min_votes=min_votes)
    if is_l2_word_lattice(lid):
        ranked = lattice_digest_l2_network(state, prefix=prefix, min_votes=min_votes)
    else:
        ranked = lattice_digest(decoded, prefix=prefix)
    if prompt.strip():
        cue_lattice = "L2_word" if is_l2_word_lattice(lid) else lid
        ranked = rank_for_cue(ranked, prompt, lattice_id=cue_lattice)

    surfaces = [concept_to_surface(cid) for cid, _ in ranked[:6]]

    if lid in ("L0_grapheme", "L0_grapheme_cyrl", "L0_grapheme_latn"):
        body = "".join(surfaces[:5]) if surfaces else "…"
        text = f"Surface L0: «{body}»."
    elif lid == "L1_syllable":
        text = f"Surface L1: {' '.join(surfaces[:4])}."
    elif lid == "L2_word":
        text = f"Surface L2: {', '.join(surfaces[:3])}."
    else:
        text = f"Surface {lid}: {', '.join(surfaces[:2])}."

    if prompt.strip():
        text = f"Слышал: «{prompt.strip()[:60]}». {text}"

    return {
        "lattice_id": lid,
        "z_level": lattices[lid].get("z_level"),
        "surface_text": text,
        "active": [{"concept_id": c, "votes": v} for c, v in ranked[:10]],
        "field_version": state.get("field_version"),
        "z_compose_count": (sss.get("last_compose") or {}).get("count"),
        "active_prism": (state.get("sn") or {}).get("active_prism"),
        "mode": (state.get("sn") or {}).get("mode", "wake"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--lattice", default=None, help="L0_grapheme | L1_syllable | L2_word | L3_phrase")
    p.add_argument("--prompt", default="")
    p.add_argument("--prompt-file", type=Path, default=None, help="UTF-8 file with cue text")
    p.add_argument("--min-votes", type=int, default=1)
    args = p.parse_args()

    prompt = args.prompt
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8").strip()

    t0 = time.perf_counter()
    state = load_field_state(args.store_dir / "field_state.json")
    out = surface_from_sss(
        state,
        lattice_id=args.lattice,
        min_votes=args.min_votes,
        prompt=prompt,
    )
    out["wall_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
