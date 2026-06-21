#!/usr/bin/env python3
"""Online listen stream — imprint + unified macro life tick per step."""

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
from casa.domain.listen_womb_tick import run_listen_womb_stream, write_womb_report
from casa.prisms.memory.agent_life import load_unified_agent_runtime, persist_unified_runtime
from casa.prisms.shared.store_layout import default_agent_store


def _find_video(bundle_dir: Path) -> Path:
    for ext in ("mp4", "webm", "mkv"):
        candidate = bundle_dir / f"video.{ext}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no video.* in {bundle_dir}")


def _resolve_wav(store_dir: Path, scene: dict[str, Any], *, manifest_dir: Path) -> Path | None:
    wav = str(scene.get("wav") or "").strip()
    if not wav:
        return None
    path = Path(wav)
    if path.is_file():
        return path
    for base in (manifest_dir, store_dir):
        candidate = base / wav
        if candidate.is_file():
            return candidate
    return None


def _load_chapter_scene(manifest: Path, chapter: int) -> dict[str, Any]:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        if int(scene.get("chapter_index", -1)) == chapter:
            return scene
    raise ValueError(f"chapter {chapter} not found in {manifest}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Listen stream driver: imprint A+V then unified macro life tick each step",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chapter", type=int, default=0)
    parser.add_argument("--store-dir", type=Path, default=None)
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between ticks")
    parser.add_argument(
        "--start",
        type=float,
        default=8.0,
        help="relative t0 inside chapter (default 8 = skip Lalabook titles)",
    )
    parser.add_argument("--end", type=float, default=None, help="relative t1 (default chapter t1)")
    parser.add_argument("--work-dir", type=Path, default=None, help="temp frames (default manifest/preview/womb_tick)")
    parser.add_argument("--report", type=Path, default=None, help="write JSON report path")
    parser.add_argument("--sleep", action="store_true", help="run_sleep once at end")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument(
        "--no-life-tick",
        action="store_true",
        help="imprint-only bench (skip TickOrchestrator macro tick)",
    )
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    bundle_dir = manifest.parent
    store_dir = (args.store_dir or default_agent_store()).resolve()
    scene = _load_chapter_scene(manifest, args.chapter)
    video_path = _find_video(bundle_dir)
    wav_path = _resolve_wav(store_dir, scene, manifest_dir=bundle_dir)
    work_dir = (args.work_dir or bundle_dir / "preview" / "womb_tick" / f"ch{args.chapter:02d}").resolve()

    chapter_t0 = float(scene.get("t0") or 0.0)
    chapter_t1 = float(scene.get("t1") or chapter_t0)
    t_end = float(args.end) if args.end is not None else chapter_t1 - chapter_t0

    use_life_tick = not args.no_life_tick
    runtime = load_unified_agent_runtime(store_dir) if use_life_tick else None
    state = runtime.state if runtime is not None else resolve_ingest_state(store_dir, None)

    state, report = run_listen_womb_stream(
        state,
        scene,
        video_path=video_path,
        wav_path=wav_path,
        work_dir=work_dir,
        store_dir=store_dir,
        interval_sec=max(0.1, float(args.interval)),
        t_start_rel=max(0.0, float(args.start)),
        t_end_rel=t_end,
        run_sleep_at_end=bool(args.sleep),
        runtime=runtime,
        run_life_tick=use_life_tick,
    )

    out: dict[str, Any] = {
        **report.to_dict(),
        "video": str(video_path),
        "wav": str(wav_path) if wav_path else None,
        "work_dir": str(work_dir),
        "store_dir": str(store_dir),
        "life_tick": use_life_tick,
    }
    if not args.no_persist:
        if runtime is not None:
            runtime.state = state
            out["persist"] = persist_unified_runtime(runtime, force=True, sync_ltm=True)
        else:
            from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

            mark_runtime_dirty(state)
            out["persist"] = save_runtime_state(
                store_dir,
                state,
                force=True,
                thin=True,
                sync_ltm_on_save=True,
            )

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.report:
        write_womb_report(args.report.resolve(), report)
        print(f"report: {args.report.resolve()}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
