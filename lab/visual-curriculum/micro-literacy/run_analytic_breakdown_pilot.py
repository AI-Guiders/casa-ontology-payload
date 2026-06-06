#!/usr/bin/env python3
"""Analytic pilot pedagogy: refresh syllable chain per word, then corpus word (separate sleeps).

Не учим analytic-probe-* frame_id — только syllable.* и lang.word на corpus frame.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import frame_by_id, steps_for_frame
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
_CURRICULUM = _MICRO.parent
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

_REPO = _CURRICULUM.parents[1]


def _corpus_frame_for_slug(manifest: dict, slug: str) -> dict | None:
    for fr in manifest.get("frames") or []:
        tags = fr.get("curriculum_tags") or []
        if f"slug:{slug}" in tags and str(fr.get("lesson_id") or "").startswith("lesson-06"):
            return fr
    return None


def run_analytic_breakdown(
    session,
    entries: list[dict],
    *,
    pilot: str = "analytic-breakdown",
) -> None:
    """Syllable chain + corpus word per entry (R1 prep, ADR-0032)."""
    from casa.prisms.visual.vis_frames import syllable_frame_id

    manifest = session.load_manifest()
    session.log({"pilot": pilot, "words": len(entries)})

    for entry in entries:
        surface = str(entry.get("surface") or "")
        slug = str(entry.get("slug") or "")
        for i, surf in enumerate(entry.get("syllables") or []):
            fid = syllable_frame_id(str(surf))
            try:
                frame = frame_by_id(manifest, fid)
            except KeyError:
                session.log({"warn": "no_syllable_frame", "slug": slug, "syllable": surf, "frame_id": fid})
                continue
            mid = f"analytic-syl-{slug}-{surf}-{i}"[:80]
            session.ingest(mid, steps_for_frame(frame), frame_id=fid)
        corp = _corpus_frame_for_slug(manifest, slug)
        if corp is None:
            session.log({"warn": "no_corpus_frame", "surface": surface, "slug": slug})
            continue
        fid = str(corp["id"])
        mid = f"analytic-word-{slug}"[:80]
        session.ingest(mid, steps_for_frame(corp), frame_id=fid)
        session.log({"surface": surface, "slug": slug, "corpus_frame": fid})


def _entries_for_args(args: argparse.Namespace) -> list[dict]:
    from literacy_lab_io import analytic_entries_for_slugs, slugs_from_phrase_events

    if args.slug:
        return analytic_entries_for_slugs([str(s) for s in args.slug])
    if args.phrase_p1:
        all_slugs = slugs_from_phrase_events()
        return analytic_entries_for_slugs(all_slugs)
    return analytic_entries_for_slugs(slugs_from_phrase_events())


def _run(session, args: argparse.Namespace) -> None:
    entries = _entries_for_args(args)
    if not entries:
        raise SystemExit("no corpus entries for breakdown (check slugs / manifest)")
    run_analytic_breakdown(session, entries, pilot=args.pilot)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slug", action="append", default=[], help="Corpus slug(s) to breakdown")
    p.add_argument("--phrase-p1", action="store_true", help="All phrase P1 words from event registry")
    p.add_argument("--pilot", default="analytic-breakdown")
    args = p.parse_args()
    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file="summary-analytic-breakdown-pilot.json",
        summary_builder=lambda s: {"moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
