#!/usr/bin/env python3
"""Listen mass ingest — manifest.ndjson → listen_moment (lexical + auditory)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.memory.listen_moment import listen_moment
from casa.prisms.memory.memory_prisms import run_sleep
from casa.prisms.memory.prism_spawn import spawn_content_lattice
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _resolve_wav(store_dir: Path, scene: dict[str, Any], *, manifest_dir: Path | None = None) -> Path | None:
    wav = str(scene.get("wav") or "").strip()
    if not wav:
        return None
    path = Path(wav)
    if path.is_file():
        return path
    for base in (manifest_dir, store_dir):
        if base is None:
            continue
        candidate = base / wav
        if candidate.is_file():
            return candidate
    return None


def ingest_listen_manifest(
    store_dir: Path,
    manifest_path: Path,
    *,
    sleep_every: int = 20,
    copies: int = 3,
    persist: bool = True,
    state: dict | None = None,
    chapter_indices: set[int] | None = None,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    manifest_path = manifest_path.resolve()
    if state is None:
        state = resolve_ingest_state(store_dir, None)
    else:
        state = ensure_prisms(state)
        spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
        spawn_content_lattice(state, "prism_memory", "L2_word", z_level=2)

    ingested = 0
    with_audio = 0
    with_visual = 0
    visual_frames_total = 0
    sleep_reports: list[dict[str, Any]] = []
    manifest_dir = manifest_path.parent

    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        ch_idx = scene.get("chapter_index")
        if chapter_indices is not None and ch_idx is not None and int(ch_idx) not in chapter_indices:
            continue
        wav_path = _resolve_wav(store_dir, scene, manifest_dir=manifest_dir)
        moment = listen_moment(
            state,
            scene,
            wav_path=wav_path,
            store_dir=store_dir,
            manifest_dir=manifest_dir,
            copies=copies,
            bundle={"claims": [], "graph": {"edges": []}},
        )
        ingested += 1
        if wav_path:
            with_audio += 1
        vcount = int(moment.get("visual_frame_count") or 0)
        if vcount > 0:
            with_visual += 1
            visual_frames_total += vcount
        if moment.get("paired_beats"):
            ac = len(moment.get("audio_beats") or [])
            if ac != vcount:
                raise ValueError(
                    f"paired beat mismatch scene {scene.get('id')}: {ac} audio vs {vcount} visual"
                )
        if sleep_every > 0 and ingested % sleep_every == 0:
            sleep_reports.append(run_sleep(state, bundle={"claims": [], "graph": {"edges": []}}))

    if sleep_every == 0 or ingested % max(sleep_every, 1) != 0:
        sleep_reports.append(run_sleep(state, bundle={"claims": [], "graph": {"edges": []}}))

    rep = {
        "store_dir": str(store_dir),
        "manifest": str(manifest_path),
        "scenes_ingested": ingested,
        "scenes_with_audio": with_audio,
        "scenes_with_visual": with_visual,
        "visual_frames_imprinted": visual_frames_total,
        "sleep": sleep_reports,
        "field_version": state.get("field_version"),
    }
    if persist:
        mark_runtime_dirty(state)
        rep["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=True,
        )
    return rep


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest listen_mass manifest (lexical + audio)")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store-dir", type=Path, default=None)
    parser.add_argument("--sleep-every", type=int, default=20)
    parser.add_argument("--copies", type=int, default=3)
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument(
        "--chapters",
        type=str,
        default="",
        help="comma chapter indices only, e.g. 0 or 0,1",
    )
    args = parser.parse_args()
    chapter_indices: set[int] | None = None
    if args.chapters.strip():
        chapter_indices = {int(x.strip()) for x in args.chapters.split(",") if x.strip()}
    rep = ingest_listen_manifest(
        args.store_dir or default_agent_store(),
        args.manifest,
        sleep_every=max(0, int(args.sleep_every)),
        copies=max(1, int(args.copies)),
        persist=not args.no_persist,
        chapter_indices=chapter_indices,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
