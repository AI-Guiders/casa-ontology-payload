#!/usr/bin/env python3
"""Build POS claims bundle: DetCorpus/freq lemmas × UD lemma→pos map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lexicon_headwords_v0 import read_headwords  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore


def build_pos_bundle(
    *,
    headwords: list[str],
    lemma_pos: dict[str, str],
    bundle_id: str,
    title: str,
    source: str,
) -> dict:
    claims: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in headwords:
        lemma = norm_word(raw)
        if not lemma or lemma in seen:
            continue
        pos_id = lemma_pos.get(lemma)
        if not pos_id or not pos_id.startswith("pos."):
            continue
        seen.add(lemma)
        claims.append({"lemma": lemma, "pos_id": pos_id})

    return {
        "bundle_id": bundle_id,
        "schema_version": 1,
        "title": title,
        "source": source,
        "claims": claims,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Build POS bundle from freq headwords + UD map")
    p.add_argument("--locale", choices=("ru", "en"), default="ru")
    p.add_argument(
        "--headwords",
        type=Path,
        default=None,
    )
    p.add_argument(
        "--lemma-pos",
        type=Path,
        default=None,
        help="JSON lemma→pos_id from fetch_ud_lemma_pos_v0.py",
    )
    p.add_argument("--top-n", type=int, default=8000, help="Max headwords from list (0=all)")
    p.add_argument("--seed", type=Path, default=None, help="Merge seed claims first (override UD)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    if args.locale == "ru":
        corpus_dir = root / "lab/corpus/ru-general-v0"
        default_out = root / "lab/kb/ru-pos-detcorpus-v1.json"
        bundle_id = "ru-pos-detcorpus-v1"
        title = "RU POS — DetCorpus lemmas × UD Russian-GSD"
        source = "detcorpus-50k-cc0 + UD_Russian-GSD"
        seed_default = root / "lab/kb/ru-pos-seed-v1.json"
    else:
        corpus_dir = root / "lab/corpus/en-general-v0"
        default_out = root / "lab/kb/en-pos-opensub-v1.json"
        bundle_id = "en-pos-opensub-v1"
        title = "EN POS — OpenSubtitles headwords × UD English-EWT"
        source = "opensubtitles-en-50k + UD_English-EWT"
        seed_default = None

    headwords_path = args.headwords or corpus_dir / "headwords.v1.txt"
    lemma_pos_path = args.lemma_pos or corpus_dir / "ud_lemma_pos.v1.json"
    out = args.out or default_out

    if not lemma_pos_path.is_file():
        raise SystemExit(f"Missing {lemma_pos_path} — run fetch_ud_lemma_pos_v0.py --locale {args.locale}")

    words = read_headwords(headwords_path)
    if args.top_n and args.top_n < len(words):
        words = words[: args.top_n]

    lemma_pos = json.loads(lemma_pos_path.read_text(encoding="utf-8"))
    bundle = build_pos_bundle(
        headwords=words,
        lemma_pos=lemma_pos,
        bundle_id=bundle_id,
        title=title,
        source=source,
    )

    if args.seed or seed_default:
        seed_path = args.seed or seed_default
        if seed_path and seed_path.is_file():
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
            by_lemma = {norm_word(c["lemma"]): c for c in bundle["claims"]}
            for row in seed.get("claims") or []:
                lemma = norm_word(str(row.get("lemma") or ""))
                if lemma:
                    by_lemma[lemma] = {"lemma": lemma, "pos_id": str(row.get("pos_id") or row.get("pos"))}
            bundle["claims"] = sorted(by_lemma.values(), key=lambda x: x["lemma"])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "bundle_id": bundle_id,
                "claims": len(bundle["claims"]),
                "headwords_in": len(words),
                "ud_map_size": len(lemma_pos),
                "out": str(out.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
