#!/usr/bin/env python3
"""Set NCA model path on state and run sleep with optional regrow."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.gen_kb_from_text import build_bundle_from_text
from casa.prisms.memory.memory_prisms import ensure_prisms, run_sleep
from casa.prisms.memory.text_tokenize import norm_text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--text", type=Path, default=Path("lab/text/corpus/kolobok-excerpt.txt"))
    p.add_argument("--lattice-id", default="L2_word", help="Lattice for NCA regrow during sleep")
    args = p.parse_args()

    bukvar = json.loads(args.bukvar.read_text(encoding="utf-8"))
    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    state.setdefault("nca", {})["model_path"] = str(args.model.resolve())
    bundle = build_bundle_from_text(norm_text(args.text.read_text(encoding="utf-8")), bukvar_bundle=bukvar)
    rep = run_sleep(state, bundle, nca_model_path=args.model, nca_lattice_id=args.lattice_id)
    save_field_state(path, state)
    print(
        json.dumps(
            {"sleep_nca": rep.get("nca"), "field_version": state.get("field_version"), "model": str(args.model)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
