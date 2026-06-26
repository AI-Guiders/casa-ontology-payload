#!/usr/bin/env python3
"""Batch cold-path ingest for Lalabook playlists → casa-listen-corpus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.prisms.shared.listen_corpus_layout import listen_corpus_root, source_bundle_dir
from tools.yt_chapters_listen_cold import _yt_dlp_cmd, cold_path_youtube_chapters

DEFAULT_PLAYLISTS = REPO / "listen_corpus" / "lalabook.playlists.json"


def _run_json(args: list[str]) -> Any:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "yt-dlp failed").strip())
    return json.loads(proc.stdout)


def list_playlist_videos(playlist_url: str) -> list[dict[str, str]]:
    data = _run_json([*_yt_dlp_cmd(), "--flat-playlist", "-J", playlist_url])
    entries = data.get("entries") or []
    out: list[dict[str, str]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "").strip()
        if not vid or vid.startswith("PL"):
            continue
        out.append({"id": vid, "title": str(row.get("title") or "").strip()})
    return out


def bundle_ready(
    corpus_root: Path,
    *,
    publisher: str,
    collection: str,
    video_id: str,
    multimodal: bool = True,
) -> bool:
    bundle = source_bundle_dir(corpus_root, publisher=publisher, collection=collection, video_id=video_id)
    if not (bundle / "audio.wav").is_file() or not (bundle / "manifest.ndjson").is_file():
        return False
    if not multimodal:
        return True
    frames = bundle / "frames"
    if frames.is_dir() and any(frames.glob("*.jpg")):
        return True
    # manifest may list frame paths before jpg extraction completes
    for line in (bundle / "manifest.ndjson").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("frame"):
            return (bundle / str(row["frame"])).is_file()
    return False


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"done": {}, "failed": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"done": {}, "failed": {}}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_batch(
    *,
    corpus_root: Path,
    playlists_path: Path,
    collections: list[str] | None = None,
    audio_only: bool = True,
    skip_existing: bool = True,
    limit_per_playlist: int | None = None,
    state_path: Path | None = None,
) -> dict[str, Any]:
    cfg = json.loads(playlists_path.read_text(encoding="utf-8"))
    publisher = str(cfg.get("publisher") or "lalabook")
    wanted = set(collections or [])
    state_file = state_path or (corpus_root / "lalabook.batch.state.json")
    state = load_state(state_file)

    summary: dict[str, Any] = {
        "corpus_root": str(corpus_root),
        "playlists": [],
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
    }

    for pl in cfg.get("playlists") or []:
        coll = str(pl.get("id") or "").strip()
        if wanted and coll not in wanted:
            continue
        url = str(pl.get("url") or "").strip()
        if not url:
            continue
        print(f"\n=== playlist {coll}: {pl.get('title')} ===", file=sys.stderr)
        try:
            videos = list_playlist_videos(url)
        except Exception as exc:
            print(f"playlist list failed: {exc}", file=sys.stderr)
            summary["playlists"].append({"id": coll, "error": str(exc)})
            continue
        if limit_per_playlist is not None:
            videos = videos[: max(0, int(limit_per_playlist))]

        pl_rep: dict[str, Any] = {"id": coll, "videos": len(videos), "ok": [], "skip": [], "fail": []}
        for idx, vid_row in enumerate(videos, start=1):
            vid = vid_row["id"]
            key = f"{coll}/{vid}"
            if skip_existing and bundle_ready(
                corpus_root, publisher=publisher, collection=coll, video_id=vid, multimodal=not audio_only
            ):
                print(f"[{idx}/{len(videos)}] skip {vid}", file=sys.stderr)
                pl_rep["skip"].append(vid)
                summary["skipped"] += 1
                continue
            if key in (state.get("done") or {}):
                print(f"[{idx}/{len(videos)}] skip cached {vid}", file=sys.stderr)
                pl_rep["skip"].append(vid)
                summary["skipped"] += 1
                continue
            watch = f"https://www.youtube.com/watch?v={vid}"
            print(f"[{idx}/{len(videos)}] fetch {vid} — {vid_row.get('title','')[:60]}", file=sys.stderr)
            try:
                rep = cold_path_youtube_chapters(
                    watch,
                    corpus_root=corpus_root,
                    publisher=publisher,
                    collection=coll,
                    fetch=True,
                    fetch_video=not audio_only,
                    with_frames=not audio_only,
                )
                state.setdefault("done", {})[key] = {
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "scenes": rep.get("scenes"),
                    "manifest": rep.get("manifest"),
                }
                pl_rep["ok"].append(vid)
                summary["downloaded"] += 1
            except Exception as exc:
                err = str(exc)
                print(f"FAIL {vid}: {err}", file=sys.stderr)
                state.setdefault("failed", {})[key] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": err}
                pl_rep["fail"].append({"id": vid, "error": err})
                summary["failed"] += 1
            save_state(state_file, state)

        summary["playlists"].append(pl_rep)

    save_state(state_file, state)
    summary["state_file"] = str(state_file)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch Lalabook playlist → listen corpus")
    parser.add_argument("--playlists", type=Path, default=DEFAULT_PLAYLISTS)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--collection", action="append", default=None, help="repeatable; default all")
    parser.add_argument("--limit-per-playlist", type=int, default=None)
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="skip video/frames (default: multimodal bind — text lives in frames, not subs)",
    )
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    rep = run_batch(
        corpus_root=(args.corpus_root or listen_corpus_root()).resolve(),
        playlists_path=args.playlists.resolve(),
        collections=args.collection,
        audio_only=args.audio_only,
        skip_existing=not args.no_skip_existing,
        limit_per_playlist=args.limit_per_playlist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if int(rep.get("failed") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
