#!/usr/bin/env python3
"""Create sss-ru-lexicon-v0 dev store: batch RU headwords + ltm export."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from export_ltm_pack_v0 import export_pack  # type: ignore
from field_write import save_field_state  # type: ignore
from boot_core_ltm_v0 import merge_core_ltm_stack  # type: ignore
from ru_lexicon_v0 import ingest_ru_lex_batch, read_headwords  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from store_layout_v0 import STORE_RU_LEXICON_V0, agent_store_dir, field_state_path  # type: ignore


def init_ru_dev_store(
    store_dir: Path,
    words: list[str],
    *,
    copies: int = 3,
) -> dict[str, Any]:
    store_dir.mkdir(parents=True, exist_ok=True)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["locale"] = "ru"
    state["store"]["corpus"] = "ru-dev-v0"

    repo = Path(__file__).resolve().parent.parent
    l0_rep = merge_core_ltm_stack(state, root=repo, include_alphabet=True, include_vk=False)
    ingest_rep = ingest_ru_lex_batch(state, words, copies=copies, configure=True)

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
                    "Russian dev lexicon for bilingual T9 demo (not full Afan corpus).",
                    "L2 shards: `L2_word_*` (corpus-quantile from headwords).",
                    "",
                    "Init:",
                    "```bash",
                    f"python tools/init_ru_dev_store_v0.py --headwords lab/exp_bilingual_v0/ru_dev_headwords.v1.txt",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    return {
        "store_dir": str(store_dir.resolve()),
        "ingest": ingest_rep,
        "l0_cyrl": l0_rep,
        "field_state": str(fs_path),
        "ltm_totals": manifest.get("totals"),
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Init RU dev lexicon store for bilingual T9 demo")
    p.add_argument(
        "--store-dir",
        type=Path,
        default=agent_store_dir(STORE_RU_LEXICON_V0, root=root),
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/ru_dev_headwords.v1.txt",
    )
    p.add_argument("--copies", type=int, default=3)
    args = p.parse_args()

    words = read_headwords(args.headwords)
    if not words:
        raise SystemExit(f"No headwords in {args.headwords}")

    rep = init_ru_dev_store(args.store_dir, words, copies=args.copies)
    rep["headwords_path"] = str(args.headwords.resolve())
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
