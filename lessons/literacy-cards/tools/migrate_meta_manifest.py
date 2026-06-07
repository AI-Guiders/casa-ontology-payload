#!/usr/bin/env python3
"""Pure-ingest: обновить concept_id в class.manifest.json на канон lang.meta.*."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meta_concepts import (  # noqa: E402
    EPISTEMIC_CHOICE,
    EPISTEMIC_CONFUSION,
    EPISTEMIC_UNKNOWN,
    GRAMMAR_POS_ACTION,
    GRAMMAR_POS_NOUN,
    GRAMMAR_POS_VERB,
    LETTER_CASE_LOWER,
    LETTER_CASE_UPPER,
    LEXICON_GRAPHEME,
    LEXICON_WORD,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "class.manifest.json"

FRAME_CONCEPT: dict[str, str] = {
    "word-bukva-sans": LEXICON_GRAPHEME,
    "word-slovo-sans": LEXICON_WORD,
    "word-zaglavnaya-sans": LETTER_CASE_UPPER,
    "word-strochnaya-sans": LETTER_CASE_LOWER,
    "word-ne_znayu-sans": EPISTEMIC_UNKNOWN,
    "word-vybor-sans": EPISTEMIC_CHOICE,
    "word-zameshatelstvo-sans": EPISTEMIC_CONFUSION,
    "word-glagol-sans": GRAMMAR_POS_VERB,
    "word-deystvie-sans": GRAMMAR_POS_ACTION,
    "word-sushchestvennoe-sans": GRAMMAR_POS_NOUN,
    "word-zaglavnaya_bukva-sans": LETTER_CASE_UPPER,
    "word-bukva_verhnego_registra-sans": LETTER_CASE_UPPER,
    "word-strochnaya_bukva-sans": LETTER_CASE_LOWER,
    "word-bukva_nizhnego_registra-sans": LETTER_CASE_LOWER,
    "word-apelsin_cap-sans": "lang.word.apelsin",
    "word-register-sssr-example-sans": "lang.word.sssr",
}

def _retag(frame: dict, concept_id: str, *, extra_tags: list[str] | None = None) -> None:
    frame["concept_id"] = concept_id
    tags = [t for t in frame.get("curriculum_tags") or [] if not str(t).startswith("lang.")]
    frame["curriculum_tags"] = [concept_id, *(extra_tags or []), *tags]


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    frames = manifest.get("frames") or []
    updated: list[str] = []
    renamed: list[str] = []
    out_frames: list[dict] = []
    for fr in frames:
        fid = str(fr.get("id") or "")
        if fid == "word-register-sssr-example-sans":
            fr = dict(fr)
            fr["id"] = "word-sssr-sans"
            fr["path"] = "lesson-07-meta-language/images/word-sssr-sans.jpg"
            fr["scene_label"] = "card:word:sssr:sans"
            _retag(fr, "lang.word.sssr", extra_tags=["register:allCaps"])
            renamed.append(f"{fid}→word-sssr-sans")
            out_frames.append(fr)
            continue
        if fid in FRAME_CONCEPT:
            fr = dict(fr)
            extra = ["register:sentenceInitial"] if fid == "word-apelsin_cap-sans" else None
            _retag(fr, FRAME_CONCEPT[fid], extra_tags=extra)
            updated.append(fid)
            out_frames.append(fr)
            continue
        out_frames.append(fr)
    manifest["frames"] = out_frames
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": updated, "renamed": renamed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
