#!/usr/bin/env python3
"""Init agent store from headword list: imprint L0+L2, export ltm/, write field_state."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from casa.prisms.memory.en_lexicon_v0 import ingest_en_lex_batch
from casa.prisms.shared.export_ltm_pack_v0 import export_pack
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.memory.boot_core_ltm_v0 import default_alphabet_core_ltm_dir, merge_core_ltm_stack
from casa.prisms.memory.grapheme_ingest_v0 import derive_graphemes_from_words, ingest_graphemes_batch
from casa.prisms.memory.lexicon_headwords_v0 import read_headwords
from casa.prisms.memory.ru_lexicon_v0 import ingest_ru_lex_batch
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.lexicon_usage_axes_v0 import (
    SOURCE_DETCORPUS,
    SOURCE_OPENSUB_EN,
    attach_axes_to_state,
    attach_en_frequency_axes,
    axes_report,
    build_modern_axes_from_frequency_jsonl,
    ru_general_frequency_path,
    write_axes_jsonl,
)
from casa.prisms.shared.store_layout_v0 import CORPUS_QUAD, agent_store_dir, field_state_path

Locale = Literal["en", "ru"]
Tier = Literal["general", "tech"]


def init_lexicon_store(
    store_dir: Path,
    words: list[str],
    *,
    locale: Locale,
    corpus: str,
    tier: Tier,
    copies: int = 3,
) -> dict[str, Any]:
    store_dir.mkdir(parents=True, exist_ok=True)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    store_meta = state.setdefault("store", {})
    store_meta["store_id"] = store_dir.name
    store_meta["locale"] = locale
    store_meta["corpus"] = corpus
    store_meta["tier"] = tier

    root = Path(__file__).resolve().parent.parent
    l0_rep: dict[str, Any] = {}
    if (default_alphabet_core_ltm_dir(root=root) / "pack.manifest.json").is_file():
        l0_rep = merge_core_ltm_stack(state, root=root, include_alphabet=True, include_vk=False)
    else:
        l0_rep = {"alphabet": "skipped — run build_alphabet_core_ltm_v0.py"}

    if locale == "en":
        ingest_rep = ingest_en_lex_batch(state, words, copies=copies, configure=True)
        on_field = int(ingest_rep.get("en_concepts_on_field") or 0)
    else:
        ingest_rep = ingest_ru_lex_batch(state, words, copies=copies, configure=True)
        on_field = int(ingest_rep.get("ru_concepts_on_field") or 0)

    axes_rep: dict[str, Any] | None = None
    if tier == "general":
        if locale == "ru":
            freq_path = ru_general_frequency_path(root=root)
            if freq_path.is_file():
                axes = build_modern_axes_from_frequency_jsonl(freq_path, source=SOURCE_DETCORPUS)
                axes_path = store_dir / "lexicon_axes.v0.jsonl"
                write_axes_jsonl(axes_path, axes)
                attach_axes_to_state(state, axes)
                axes_rep = axes_report(axes)
        elif locale == "en":
            axes_rep = attach_en_frequency_axes(state, root=root, store_dir=store_dir)

    fs_path = field_state_path(store_dir)
    save_field_state(fs_path, state, compact=True)
    manifest = export_pack(state, store_dir / "ltm")

    memory_md = store_dir / "MEMORY.md"
    if not memory_md.is_file():
        shard_hint = "L2_en_word_*" if locale == "en" else "L2_word_*"
        memory_md.write_text(
            "\n".join(
                [
                    f"# {store_dir.name}",
                    "",
                    f"**Locale:** {locale} | **Tier:** {tier} | **Corpus:** {corpus}",
                    "",
                    f"L2 shards: `{shard_hint}`. Cold add: `lexicon_cold_ingest_v0.py`.",
                    "",
                    "Train NCA (CUDA):",
                    "```bash",
                    f"python tools/train_sss_nca_shards_v0.py --store-dir lab/agent-stores/{store_dir.name} --layer all --device cuda",
                    f"python tools/nca_registry_v0.py --sync-registry --store-dir lab/agent-stores/{store_dir.name}",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    return {
        "store_dir": str(store_dir.resolve()),
        "locale": locale,
        "tier": tier,
        "corpus": corpus,
        "words_unique": len(words),
        "concepts_on_field": on_field,
        "ingest": ingest_rep,
        "l0": l0_rep,
        "field_state": str(fs_path),
        "ltm_totals": manifest.get("totals"),
        "l2_sharding": state.get("l2_sharding"),
        "lexicon_axes": axes_rep,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Init lexicon store from headwords file")
    p.add_argument("--corpus-id", choices=tuple(CORPUS_QUAD.keys()), default=None)
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--headwords", type=Path, default=None)
    p.add_argument("--locale", choices=("en", "ru"), default=None)
    p.add_argument("--tier", choices=("general", "tech"), default=None)
    p.add_argument("--copies", type=int, default=3)
    args = p.parse_args()

    if args.corpus_id:
        spec = CORPUS_QUAD[args.corpus_id]
        store_dir = args.store_dir or agent_store_dir(spec.store_id, root=root)
        headwords = args.headwords or (root / spec.headwords_rel)
        locale = spec.locale
        tier = spec.tier
        corpus = spec.corpus_tag
    else:
        if not args.store_dir or not args.headwords or not args.locale or not args.tier:
            raise SystemExit("Provide --corpus-id or all of --store-dir --headwords --locale --tier")
        store_dir = args.store_dir
        headwords = args.headwords
        locale = args.locale
        tier = args.tier
        corpus = f"{locale}-{tier}-v0"

    words = read_headwords(headwords)
    if not words:
        raise SystemExit(f"No headwords in {headwords}")

    rep = init_lexicon_store(
        store_dir,
        words,
        locale=locale,
        corpus=corpus,
        tier=tier,
        copies=args.copies,
    )
    rep["headwords_path"] = str(Path(headwords).resolve())
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
