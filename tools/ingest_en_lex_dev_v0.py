#!/usr/bin/env python3
"""Ingest dev English headwords onto L2 via listen_word (lab bilingual v0).

Latin graphemes are not in RU_DICT_ALPHABET; route_l2_lattice / lex_sort_key
assigns them to the lex_sort "other" bucket (first_letter_index == len(alpha)).
That is acceptable for dev — no EN_DICT_ALPHABET shard plan yet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from field_write import save_field_state  # type: ignore
from predictor_v0 import _L2_PREFIX_INDEX_CACHE  # type: ignore
from sss_l2_shard_v0 import lattice_digest_l2_network, L2_CONCEPT_PREFIX  # type: ignore
from sss_vocab_v0 import listen_word, norm_word  # type: ignore
from store_boot_v0 import boot_store  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore


def read_headwords(path: Path) -> list[str]:
    words: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        w = norm_word(line.split("#", 1)[0])
        if w and not w.startswith("#"):
            words.append(w)
    return list(dict.fromkeys(words))


def ingest_en_lex(
    state: dict,
    words: list[str],
    *,
    copies: int = 3,
    link_scene: bool = False,
) -> dict[str, Any]:
    heard: list[dict[str, Any]] = []
    shards: dict[str, int] = {}
    for w in words:
        rep = listen_word(state, w, copies=copies, link_scene=link_scene)
        heard.append(rep)
        lid = str(rep.get("lattice_id") or "")
        shards[lid] = shards.get(lid, 0) + 1

    state.pop(_L2_PREFIX_INDEX_CACHE, None)
    digest = lattice_digest_l2_network(state)
    en_on_field = sum(
        1
        for cid, _ in digest
        if cid.startswith(L2_CONCEPT_PREFIX) and norm_word(cid[len(L2_CONCEPT_PREFIX) :]) in set(words)
    )
    return {
        "words_requested": len(words),
        "words_heard": len(heard),
        "en_concepts_on_field": en_on_field,
        "shard_histogram": dict(sorted(shards.items())),
        "field_version": state.get("field_version"),
        "sample": heard[:5],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest EN dev headwords onto L2 (listen_word)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--headwords",
        type=Path,
        default=Path("examples/exp_bilingual_v0/en_dev_headwords.v1.txt"),
    )
    p.add_argument("--copies", type=int, default=3)
    p.add_argument("--write", action="store_true", help="Persist merged state to field_state.json")
    args = p.parse_args()

    words = read_headwords(args.headwords)
    if not words:
        raise SystemExit(f"No headwords in {args.headwords}")

    boot = boot_store(args.store_dir, prefer_field_state=False)
    rep = ingest_en_lex(boot["state"], words, copies=args.copies)
    rep["boot"] = {
        "source": boot.get("source"),
        "l2_shard_count": boot.get("l2_shard_count"),
    }
    rep["headwords_path"] = str(args.headwords.resolve())

    if args.write:
        out = field_state_path(args.store_dir)
        save_field_state(out, boot["state"], compact=True)
        rep["written"] = str(out)
        rep["write_note"] = (
            "bench_en_t9_smoke_v0 --prefer-field-state loads field_state without import_pack; "
            "boot_store --prefer-field-state re-imports ltm/ and drops EN overlay."
        )

    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
