#!/usr/bin/env python3
"""Build a WIDE conceptual network (~2.5k concepts) by classifying nouns with WordNet.

Layers a large auto-classified vocabulary on top of the hand-curated core
(scripts/build_concept_net.py). Russian nouns + English glosses come from the OpenRussian
nouns CSV (Badestrand/russian-dictionary, CC BY-SA); each English noun's category comes
from its dominant WordNet supersense (noun.animal -> animal, noun.food -> food,
noun.artifact -> artifact, …). The curated core keeps its fine affordances (furniture ->
support_surface, vehicle -> rideable); the WordNet layer gets coarse supersense-level
affordances. Build-time only (needs nltk + wordnet); the output JSON is what ships.

    pip install nltk && python -c "import nltk; nltk.download('wordnet')"
    python scripts/build_concept_net_wordnet.py --out lab/curriculum/concept-net-wide-v1.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request
from collections import Counter

import build_concept_net as core  # CATEGORIES, CONCEPTS, RELATIONS, PARTS, VALID, INVALID

NOUNS_URL = "https://raw.githubusercontent.com/Badestrand/russian-dictionary/master/nouns.csv"
RU = re.compile(r"^[а-яё]+$")
EN = re.compile(r"^[a-z]+$")
_LEAD = ("a ", "an ", "the ", "to ")

# WordNet supersense -> our category. Categories not in the core are added below.
LEX2CAT = {
    "noun.animal": "animal", "noun.person": "person", "noun.plant": "plant",
    "noun.food": "food", "noun.body": "body_part", "noun.substance": "substance",
    "noun.artifact": "artifact", "noun.location": "place", "noun.object": "physical_object",
}  # everything else -> abstract

EXTRA_CATEGORIES = [
    {"id": "artifact", "isa": ["physical_object"], "affords": ["ownable"]},  # positionable via physical_object
]


def first_en(s: str) -> str:
    seg = re.split(r"[,;(/]", (s or "").strip())[0].strip().lower()
    for lead in _LEAD:
        if seg.startswith(lead):
            seg = seg[len(lead):].strip()
    return seg


def _read_nouns(path: str | None) -> list[dict]:
    text = (
        open(path, encoding="utf-8").read() if path
        else urllib.request.urlopen(NOUNS_URL).read().decode("utf-8")  # noqa: S310
    )
    return list(csv.DictReader(text.splitlines(), delimiter="\t"))


def build(nouns_path: str | None, target: int) -> dict:
    from nltk.corpus import wordnet as wn

    def supersense(word: str) -> str | None:
        syns = wn.synsets(word, pos="n")
        if not syns:
            return None
        c: Counter = Counter()
        for sy in syns:
            c[sy.lexname()] += sum(l.count() for l in sy.lemmas()) or 1
        return c.most_common(1)[0][0]

    # start from the curated core
    concepts: dict[str, list[list[str]]] = {cat: [list(p) for p in members] for cat, members in core.CONCEPTS.items()}
    core_en = {en.lower() for members in core.CONCEPTS.values() for _ru, en in members}
    core_ru = {ru.lower() for members in core.CONCEPTS.values() for ru, _en in members}
    categories = list(core.CATEGORIES) + EXTRA_CATEGORIES
    cat_ids = {c["id"] for c in categories}

    added = 0
    for row in _read_nouns(nouns_path):
        if added >= target:
            break
        ru = (row.get("bare") or "").strip().lower()
        en = first_en(row.get("translations_en") or "")
        # skip if the word (either side) already belongs to a core or added concept —
        # don't create competing synonyms that would shadow the curated concepts
        if not RU.match(ru) or not EN.match(en) or len(en) < 2 or len(ru) < 2:
            continue
        if en in core_en or ru in core_ru:
            continue
        cat = LEX2CAT.get(supersense(en) or "", "abstract")
        if cat not in cat_ids:
            continue
        concepts.setdefault(cat, []).append([ru, en])
        core_en.add(en)
        core_ru.add(ru)
        added += 1

    return {
        "name": "concept-net-wide-v1",
        "description": (
            "Wide conceptual network: the curated core (fine affordances) plus a large "
            "WordNet-supersense-classified vocabulary from OpenRussian (CC BY-SA). Core types "
            "keep their precise affordances; the WordNet layer is coarse (supersense-level). "
            "Auto-classified by dominant WordNet sense — type/affordance checking, not full physics."
        ),
        "lattice_id": "schema-math",
        "categories": categories,
        "concepts": {cat: members for cat, members in concepts.items() if members},
        "relations": core.RELATIONS,
        "parts": [list(p) for p in core.PARTS],
        "valid": core.VALID,
        "invalid": core.INVALID,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nouns", default=".tmp/nouns.csv", help="local OpenRussian nouns.csv (else download)")
    ap.add_argument("--target", type=int, default=2200, help="WordNet concepts to add on top of the core")
    args = ap.parse_args()
    import os

    data = build(args.nouns if os.path.exists(args.nouns) else None, args.target)
    n = sum(len(v) for v in data["concepts"].values())
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    print(f"wrote {n} concepts in {len(data['concepts'])} categories to {args.out}")


if __name__ == "__main__":
    main()
