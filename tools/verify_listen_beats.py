#!/usr/bin/env python3
"""Pre-ingest gate: validate paired scene-cut beats before listen_mass_ingest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.domain.listen_beat_verify import format_beat_report, validate_scene_beats


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify listen manifest beats before ingest")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--chapters",
        type=str,
        default="",
        help="comma chapter indices; default all lines",
    )
    parser.add_argument("--require-paired", action="store_true", default=True)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    bundle_dir = manifest.parent
    want: set[int] | None = None
    if args.chapters.strip():
        want = {int(x.strip()) for x in args.chapters.split(",") if x.strip()}

    failed = 0
    passed = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        idx = scene.get("chapter_index")
        if want is not None and idx is not None and int(idx) not in want:
            continue
        check = validate_scene_beats(scene, bundle_dir, require_paired=args.require_paired)
        title = str(scene.get("chapter_title") or scene.get("caption") or scene.get("id") or "")
        print(format_beat_report(check, scene_title=title))
        print()
        if check.ok:
            passed += 1
        else:
            failed += 1

    if passed == 0 and failed == 0:
        print("no chapters matched", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
