#!/usr/bin/env python3
"""Ingest room photos → von-neumann LRGB visual imprint (ADR-0028 S2a)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.store_layout import STORE_AGENT_DEFAULT, default_agent_store
from casa.prisms.visual.ingest_room import ingest_room_frames
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest RGB images into prism_visual (LRGB)")
    p.add_argument("--store-dir", type=Path, default=None, help="Agent store (default von-neumann)")
    p.add_argument(
        "--images",
        type=Path,
        nargs="*",
        help="Image files (jpg/png/ppm). Default: lab/sensory/room/*.ppm",
    )
    p.add_argument("--scene-label", default="room")
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument(
        "--write-sample",
        action="store_true",
        help="Write lab/sensory/room/sample-room.ppm (synthetic) and ingest it",
    )
    args = p.parse_args()

    store_dir = (args.store_dir or default_agent_store(root=REPO_ROOT)).resolve()
    room_dir = REPO_ROOT / "lab" / "sensory" / "room"
    room_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = list(args.images or [])
    if args.write_sample or not paths:
        sample = room_dir / "sample-room.ppm"
        write_synthetic_room_ppm(sample)
        paths = [sample]
    if not paths:
        paths = sorted(room_dir.glob("*.ppm")) + sorted(room_dir.glob("*.png")) + sorted(
            room_dir.glob("*.jpg")
        )

    report = ingest_room_frames(
        store_dir,
        paths,
        scene_label=args.scene_label,
        sleep_after_each=not args.no_sleep,
        persist=True,
    )
    out_path = room_dir / "last-ingest-report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
