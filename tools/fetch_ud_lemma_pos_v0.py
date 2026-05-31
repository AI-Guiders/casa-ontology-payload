#!/usr/bin/env python3
"""Download UD CoNLL-U → lemma→UPOS map (RU/EN) for POS bundle build."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

from sss_vocab_v0 import norm_word  # type: ignore

UD_CORPORA = {
    "ru": [
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Russian-GSD/master/ru_gsd-ud-train.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Russian-GSD/master/ru_gsd-ud-dev.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_Russian-GSD/master/ru_gsd-ud-test.conllu",
    ],
    "en": [
        "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-train.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-dev.conllu",
        "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-test.conllu",
    ],
}

RU_LEMMA_RE = re.compile(r"^[а-яё]+(?:-[а-яё]+)?$", re.IGNORECASE)
EN_LEMMA_RE = re.compile(r"^[a-z]+(?:[-'][a-z]+)?$")

UPOS_TO_POS: dict[str, str] = {
    "NOUN": "pos.noun",
    "PROPN": "pos.propn",
    "VERB": "pos.verb",
    "ADJ": "pos.adj",
    "ADV": "pos.adv",
    "PRON": "pos.pron",
    "ADP": "pos.adp",
    "CCONJ": "pos.conj",
    "SCONJ": "pos.conj",
    "PART": "pos.part",
    "DET": "pos.det",
    "NUM": "pos.num",
    "INTJ": "pos.intj",
    "AUX": "pos.verb",
    "SYM": "pos.x",
    "X": "pos.x",
    "PUNCT": "",
}


def rel_to_root(path: Path, root: Path) -> str:
    """Repo-relative posix path for manifests (no absolute machine paths in tracked files)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as resp:
        dest.write_bytes(resp.read())


def parse_conllu(path: Path, *, locale: str) -> dict[str, Counter[str]]:
    lemma_re = RU_LEMMA_RE if locale == "ru" else EN_LEMMA_RE
    counts: dict[str, Counter[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 4 or cols[0].startswith("-"):
            continue
        lemma = norm_word(cols[2])
        upos = cols[3].strip().upper()
        pos_id = UPOS_TO_POS.get(upos, "")
        if not lemma or not pos_id or not lemma_re.match(lemma):
            continue
        counts.setdefault(lemma, Counter())[pos_id] += 1
    return counts


def merge_counts(parts: list[dict[str, Counter[str]]]) -> dict[str, str]:
    merged: dict[str, Counter[str]] = {}
    for block in parts:
        for lemma, ctr in block.items():
            merged.setdefault(lemma, Counter()).update(ctr)
    return {lemma: ctr.most_common(1)[0][0] for lemma, ctr in merged.items()}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Fetch UD lemma→pos map")
    p.add_argument("--locale", choices=("ru", "en"), default="ru")
    p.add_argument("--cache-dir", type=Path, default=None)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON object lemma→pos_id",
    )
    p.add_argument("--refresh", action="store_true")
    args = p.parse_args()

    cache_dir = args.cache_dir or root / f"lab/corpus/{args.locale}-general-v0/source/ud"
    out = args.out or root / f"lab/corpus/{args.locale}-general-v0/ud_lemma_pos.v1.json"

    parts: list[dict[str, Counter[str]]] = []
    for url in UD_CORPORA[args.locale]:
        name = url.rsplit("/", 1)[-1]
        dest = cache_dir / name
        if args.refresh or not dest.is_file():
            print(f"Downloading {url} …", flush=True)
            download(url, dest)
        parts.append(parse_conllu(dest, locale=args.locale))

    lemma_pos = merge_counts(parts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lemma_pos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = out.parent / "ud_pos.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "locale": args.locale,
                "source": "Universal Dependencies",
                "corpus_urls": UD_CORPORA[args.locale],
                "lemma_count": len(lemma_pos),
                "out": rel_to_root(out, root),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    sample = dict(list(lemma_pos.items())[:8])
    print(
        json.dumps(
            {"locale": args.locale, "lemmas": len(lemma_pos), "out": str(out), "sample": sample},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
