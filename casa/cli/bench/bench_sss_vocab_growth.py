#!/usr/bin/env python3
"""Pass 1 vs pass 2: discovered vs reinforced vocabulary."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from gen_kb_from_text_v0 import build_bundle_from_text  # type: ignore
from sss_cylinders_v0 import ensure_prisms, run_sleep  # type: ignore
from sss_text_ingest_v0 import ingest_text  # type: ignore
from sss_text_listen_field_v0 import ingest_text_field  # type: ignore
from sss_text_tokenize_v0 import extract_words, norm_text  # type: ignore
from sss_vocab_v0 import word_votes_from_field  # type: ignore


def growth_pass(
    state: dict,
    text: str,
    *,
    bukvar: dict,
    listen_copies: int,
    sleep: bool,
    use_field: bool,
) -> dict:
    before = word_votes_from_field(state)
    fn = ingest_text_field if use_field else ingest_text
    rep = fn(
        state,
        text,
        bukvar_bundle=bukvar,
        listen_copies=listen_copies,
        sleep=False,
    )
    if sleep:
        dynamic = build_bundle_from_text(text, bukvar_bundle=bukvar)
        run_sleep(state, dynamic)
    after = word_votes_from_field(state)
    words = extract_words(text)
    discovered = [w for w in words if before.get(w, 0) == 0 and after.get(w, 0) > 0]
    reinforced = [w for w in words if before.get(w, 0) > 0 and after.get(w, 0) > before.get(w, 0)]
    return {
        "discovered": discovered,
        "reinforced": reinforced,
        "ingest": rep.get("extract"),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--listen-copies", type=int, default=2)
    p.add_argument("--field", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bukvar = json.loads(args.bukvar.read_text(encoding="utf-8"))
    text = norm_text(args.text.read_text(encoding="utf-8"))
    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))

    pass1 = growth_pass(state, text, bukvar=bukvar, listen_copies=args.listen_copies, sleep=True, use_field=args.field)
    pass2 = growth_pass(state, text, bukvar=bukvar, listen_copies=args.listen_copies, sleep=True, use_field=args.field)
    save_field_state(path, state)

    report = {
        "pass1": pass1,
        "pass2": pass2,
        "growth_ok": len(pass1["discovered"]) > 0 and len(pass2["reinforced"]) > 0,
        "use_field": args.field,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
