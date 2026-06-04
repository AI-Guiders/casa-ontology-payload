#!/usr/bin/env python3
"""Quick probe: ё vs е vs ю on von-neumann."""

from __future__ import annotations

from probe_infra import manifest_hints, run_frame_probe

FRAMES = (
    "letter-yo-lower-sans",
    "letter-yo-upper-sans",
    "letter-e-lower-sans",
    "letter-e-upper-sans",
    "letter-yu-lower-sans",
    "letter-yu-upper-sans",
)

YO_WORD_FRAMES = (
    "word-ac6d35c17aca-sans",  # ещё (corpus)
    "word-cc4191f658c9-sans",  # её (closed class)
)


def _yo_word_frames() -> tuple[str, ...]:
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo / "lessons/literacy-cards/class.manifest.json").read_text(encoding="utf-8"))
    extra: list[str] = []
    for surface in ("ребёнок", "зелёный", "чёрный"):
        for f in manifest.get("frames") or []:
            tags = f.get("curriculum_tags") or []
            if any(t == f"word:{surface}" for t in tags):
                extra.append(str(f["id"]))
                break
    return YO_WORD_FRAMES + tuple(extra)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--words", action="store_true", help="probe whole words with ё")
    args = p.parse_args()
    frames = _yo_word_frames() if args.words else FRAMES
    probe = "yo-words-check" if args.words else "yo-letter-check"
    report = "teacher-yo-words-check.json" if args.words else "teacher-yo-letter-check.json"
    hints = manifest_hints()

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    run_frame_probe(
        probe=probe,
        frames=frames,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename=report,
        lock_holder=f"probe:{probe}",
        print_lines=True,
    )


if __name__ == "__main__":
    main()
