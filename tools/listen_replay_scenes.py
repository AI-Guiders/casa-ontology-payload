#!/usr/bin/env python3
"""Replay imprinted listen scenes through life tick (wire-gap W8, phase B)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.domain.listen_womb_tick import run_listen_womb_stream
from casa.prisms.auditory.imprint import auditory_tokens_on_field
from casa.prisms.memory.agent_life import load_unified_agent_runtime, persist_unified_runtime
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.visual.imprint import visual_tokens_on_field
from casa.sensory.adapters import find_bundle_video, resolve_scene_wav


def scene_has_sensory_imprint(state: dict, scene_id: str) -> bool:
    sid = str(scene_id or "").strip()
    if not sid:
        return False
    return bool(auditory_tokens_on_field(state, sid) or visual_tokens_on_field(state, sid))


def _load_replay_log(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"scenes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"scenes": {}}


def replay_listen_manifest(
    store_dir: Path,
    manifest_path: Path,
    *,
    chapter_indices: set[int] | None = None,
    interval_sec: float = 0.5,
    t_start_rel: float = 8.0,
    t_end_rel: float | None = None,
    work_root: Path | None = None,
    replay_log: Path | None = None,
    skip_unchanged: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    manifest_path = manifest_path.resolve()
    bundle_dir = manifest_path.parent
    runtime = load_unified_agent_runtime(store_dir)
    state = runtime.state
    log = _load_replay_log(replay_log) if replay_log else {"scenes": {}}
    scenes_log = log.setdefault("scenes", {})

    chapters: list[dict[str, Any]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        ch = scene.get("chapter_index")
        if chapter_indices is not None and ch is not None and int(ch) not in chapter_indices:
            continue
        chapters.append(scene)

    video_path = find_bundle_video(bundle_dir)
    reports: list[dict[str, Any]] = []
    skipped: list[str] = []

    for scene in chapters:
        sid = str(scene.get("id") or "")
        if not scene_has_sensory_imprint(state, sid):
            skipped.append(sid or "?")
            continue
        fv = int(state.get("field_version") or 0)
        prev = scenes_log.get(sid) if isinstance(scenes_log.get(sid), dict) else {}
        if skip_unchanged and int(prev.get("field_version") or -1) == fv:
            skipped.append(sid)
            continue

        ch = int(scene.get("chapter_index") or 0)
        wav_path = resolve_scene_wav(store_dir, scene, manifest_dir=bundle_dir)
        work_dir = (work_root or bundle_dir / "preview" / "replay" / f"ch{ch:02d}").resolve()
        chapter_t1 = float(scene.get("t1") or scene.get("t0") or 0.0) - float(scene.get("t0") or 0.0)
        t_end = float(t_end_rel) if t_end_rel is not None else chapter_t1

        state, report = run_listen_womb_stream(
            state,
            scene,
            video_path=video_path,
            wav_path=wav_path,
            work_dir=work_dir,
            store_dir=store_dir,
            interval_sec=max(0.1, interval_sec),
            t_start_rel=max(0.0, t_start_rel),
            t_end_rel=t_end,
            runtime=runtime,
            run_life_tick=True,
        )
        runtime.state = state
        row = {
            "scene_id": sid,
            "chapter": ch,
            "summary": report.summary(),
            "field_version": int(state.get("field_version") or 0),
        }
        reports.append(row)
        scenes_log[sid] = {
            "field_version": row["field_version"],
            "life_tick_count": row["summary"].get("life_tick_count"),
            "life_surprise_ticks": row["summary"].get("life_surprise_ticks"),
        }

    out: dict[str, Any] = {
        "store_dir": str(store_dir),
        "manifest": str(manifest_path),
        "replayed": len(reports),
        "skipped": skipped,
        "reports": reports,
        "field_version": int(state.get("field_version") or 0),
    }
    if replay_log:
        replay_log.parent.mkdir(parents=True, exist_ok=True)
        replay_log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out["replay_log"] = str(replay_log)
    if persist:
        out["persist"] = persist_unified_runtime(runtime, force=True, sync_ltm=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay imprinted Lalabook scenes via unified life tick")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store-dir", type=Path, default=None)
    parser.add_argument("--chapters", type=str, default="", help="comma-separated chapter indices, e.g. 0,1")
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--start", type=float, default=8.0)
    parser.add_argument("--end", type=float, default=None)
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--replay-log", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="replay even if field_version unchanged")
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    chapters: set[int] | None = None
    if args.chapters.strip():
        chapters = {int(x.strip()) for x in args.chapters.split(",") if x.strip()}

    out = replay_listen_manifest(
        (args.store_dir or default_agent_store()).resolve(),
        args.manifest.resolve(),
        chapter_indices=chapters,
        interval_sec=args.interval,
        t_start_rel=args.start,
        t_end_rel=args.end,
        work_root=args.work_root,
        replay_log=args.replay_log,
        skip_unchanged=not args.force,
        persist=not args.no_persist,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
