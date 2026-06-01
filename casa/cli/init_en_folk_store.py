#!/usr/bin/env python3
"""Create lexicon-en-folk store: batch ingest EN folk headwords + export ltm/."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.en_lexicon import ingest_en_lex_batch, read_headwords
from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.memory.grapheme_ingest import derive_graphemes_from_words, ingest_graphemes_batch
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.lexicon_usage_axes import attach_en_frequency_axes
from casa.prisms.shared.store_layout import STORE_EN_FOLK_V0, agent_store_dir, field_state_path


def init_en_folk_store(
    store_dir: Path,
    words: list[str],
    *,
    copies: int = 3,
) -> dict[str, Any]:
    store_dir.mkdir(parents=True, exist_ok=True)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["locale"] = "en"
    state["store"]["corpus"] = "en-folk"

    ingest_rep = ingest_en_lex_batch(state, words, copies=copies, configure=True)
    latn_chars = derive_graphemes_from_words(words, "latn")
    l0_rep = ingest_graphemes_batch(state, latn_chars, "latn", copies=max(3, copies))

    root = Path(__file__).resolve().parent.parent
    axes_rep = attach_en_frequency_axes(state, root=root, store_dir=store_dir)

    fs_path = field_state_path(store_dir)
    save_field_state(fs_path, state, compact=True)

    ltm_dir = store_dir / "ltm"
    manifest = export_pack(state, ltm_dir)

    memory_md = store_dir / "MEMORY.md"
    if not memory_md.is_file():
        memory_md.write_text(
            "\n".join(
                [
                    f"# {store_dir.name}",
                    "",
                    "English folk-tale lexicon (Grimm + Jacobs via Gutenberg).",
                    "L2 shards: `L2_en_word_*` (crc32, 16 shards).",
                    "L0: `grapheme.latn.*` derived from lexicon (no tags).",
                    "",
                    "Boot:",
                    f"```bash",
                    f"python tools/store_boot.py --store-dir lab/agent-stores/{store_dir.name}",
                    f"```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    return {
        "store_dir": str(store_dir.resolve()),
        "ingest": ingest_rep,
        "l0_latn": l0_rep,
        "field_state": str(fs_path),
        "ltm_totals": manifest.get("totals"),
        "l2_sharding": state.get("l2_sharding"),
        "lexicon_axes": axes_rep,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Init EN folk store (batch L2 + ltm export)")
    p.add_argument(
        "--store-dir",
        type=Path,
        default=root / "lab/agent-stores" / STORE_EN_FOLK_V0,
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual/en_folk_headwords.v1.txt",
    )
    p.add_argument("--copies", type=int, default=3)
    args = p.parse_args()

    words = read_headwords(args.headwords)
    if not words:
        raise SystemExit(f"No headwords in {args.headwords}")

    rep = init_en_folk_store(args.store_dir, words, copies=args.copies)
    rep["headwords_path"] = str(args.headwords.resolve())
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
