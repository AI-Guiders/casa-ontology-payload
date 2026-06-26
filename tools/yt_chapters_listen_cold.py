#!/usr/bin/env python3
"""YouTube chapters → listen_mass manifest (bind profile, no word cards).

Downloads media into CASA_LISTEN_CORPUS (default: sibling ``casa-listen-corpus/``),
not into lab/ or agents/. Repo tracks only listen_corpus/README.md.

Requires: yt-dlp, ffmpeg (for frames).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.prisms.shared.listen_corpus_layout import listen_corpus_root, source_bundle_dir
from casa.sensory.chapter_scene_cuts import extract_chapter_beats

_CHAPTER_LINE = re.compile(
    r"^(?P<t0>\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<title>.+)$",
)


def _slug(text: str) -> str:
    out: list[str] = []
    for ch in str(text or "").strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "scene"


def youtube_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/")[0]
    if "youtube.com" in (parsed.hostname or ""):
        q = parse_qs(parsed.query)
        if q.get("v"):
            return str(q["v"][0])
    raise ValueError(f"cannot parse YouTube video id from {url!r}")


def _parse_clock(ts: str) -> float:
    parts = ts.strip().split(":")
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s.replace(",", "."))
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))
    raise ValueError(f"bad timestamp {ts!r}")


def _finalize_chapter_windows(rows: list[dict[str, Any]], *, duration: float) -> list[dict[str, Any]]:
    if not rows:
        return []
    ordered = sorted(rows, key=lambda r: float(r["t0"]))
    deduped: list[dict[str, Any]] = []
    for row in ordered:
        t0 = float(row["t0"])
        if deduped and abs(t0 - float(deduped[-1]["t0"])) < 0.5:
            if len(str(row.get("title") or "")) > len(str(deduped[-1].get("title") or "")):
                deduped[-1] = row
            continue
        deduped.append(row)
    dur = max(float(duration or 0.0), float(deduped[-1]["t0"]) + 1.0)
    for i, row in enumerate(deduped):
        row["index"] = i
        row["t1"] = float(deduped[i + 1]["t0"]) if i + 1 < len(deduped) else dur
    return deduped


def _chapters_from_yt_api(info: dict[str, Any]) -> list[dict[str, Any]]:
    raw = info.get("chapters")
    if not isinstance(raw, list) or not raw:
        return []
    out: list[dict[str, Any]] = []
    for idx, ch in enumerate(raw):
        if not isinstance(ch, dict):
            continue
        title = str(ch.get("title") or f"chapter-{idx:02d}").strip()
        t0 = float(ch.get("start_time") or 0.0)
        out.append({"title": title, "t0": t0})
    return out


def _chapters_from_description(info: dict[str, Any]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for line in str(info.get("description") or "").splitlines():
        m = _CHAPTER_LINE.match(line.strip())
        if not m:
            continue
        parsed.append(
            {
                "title": m.group("title").strip(),
                "t0": _parse_clock(m.group("t0")),
            }
        )
    return parsed


def chapters_from_yt_info(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefer fuller chapter list — Lalabook often has 15 lines in description, 2 in API."""
    duration = float(info.get("duration") or 0.0)
    from_api = _chapters_from_yt_api(info)
    from_desc = _chapters_from_description(info)
    source = from_desc if len(from_desc) > len(from_api) else from_api
    if not source:
        return []
    return _finalize_chapter_windows(source, duration=duration)


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=cwd, check=True)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _yt_dlp_cmd() -> list[str]:
    if _which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def _ffmpeg_cmd() -> list[str]:
    path = _which("ffmpeg")
    if path:
        return [path]
    raise RuntimeError("ffmpeg not found on PATH")


def fetch_youtube_bundle(
    url: str,
    out_dir: Path,
    *,
    fetch_video: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ytdlp = _yt_dlp_cmd()

    info_path = out_dir / "video.info.json"
    if not info_path.is_file():
        _run(
            [
                *ytdlp,
                "--skip-download",
                "--write-info-json",
                "--no-playlist",
                "-o",
                str(out_dir / "video.%(ext)s"),
                url,
            ]
        )

    info = json.loads(info_path.read_text(encoding="utf-8"))
    audio_wav = out_dir / "audio.wav"
    if not audio_wav.is_file():
        _run(
            [
                *ytdlp,
                "-f",
                "bestaudio/best",
                "-x",
                "--audio-format",
                "wav",
                "--no-playlist",
                "-o",
                str(out_dir / "audio.%(ext)s"),
                url,
            ]
        )

    video_path: Path | None = None
    if fetch_video:
        for ext in ("mp4", "mkv", "webm"):
            candidate = out_dir / f"video.{ext}"
            if candidate.is_file():
                video_path = candidate
                break
        if video_path is None:
            _run(
                [
                    *ytdlp,
                    "-f",
                    "bv*[height<=720]+ba/b[height<=720]/best",
                    "--no-playlist",
                    "-o",
                    str(out_dir / "video.%(ext)s"),
                    url,
                ]
            )
            for ext in ("mp4", "mkv", "webm"):
                candidate = out_dir / f"video.{ext}"
                if candidate.is_file():
                    video_path = candidate
                    break

    return {
        "info": info,
        "audio_wav": audio_wav if audio_wav.is_file() else None,
        "video_path": video_path,
    }


def extract_chapter_burst(
    video_path: Path,
    *,
    t0: float,
    t1: float,
    out_dir: Path,
    chapter_index: int,
    slug: str,
    interval_sec: float = 12.0,
    min_frames: int = 4,
    max_frames: int = 24,
    scene_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    """Scene-cut paired beats (default). ``interval_sec`` kept for API compat only."""
    _ = interval_sec
    chapter_frames_dir = out_dir / f"{int(chapter_index):02d}-{slug}"
    beats = extract_chapter_beats(
        video_path,
        t0=t0,
        t1=t1,
        out_dir=chapter_frames_dir,
        chapter_index=chapter_index,
        slug=slug,
        scene_threshold=scene_threshold,
        min_beats=min_frames,
        max_beats=max_frames,
    )
    return beats


def extract_chapter_frame(video_path: Path, *, t_sec: float, out_jpg: Path) -> bool:
    try:
        ffmpeg = _ffmpeg_cmd()
    except RuntimeError:
        return False
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            *ffmpeg,
            "-y",
            "-ss",
            f"{t_sec:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out_jpg),
        ]
    )
    return out_jpg.is_file()


def build_chapter_manifest(
    *,
    bundle_dir: Path,
    info: dict[str, Any],
    publisher: str,
    collection: str,
    speaker: str,
    profile: str,
    with_frames: bool,
    video_path: Path | None,
    frame_interval_sec: float = 12.0,
    min_frames_per_chapter: int = 4,
    max_frames_per_chapter: int = 40,
    scene_cut_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    video_id = str(info.get("id") or bundle_dir.name)
    source = f"{_slug(publisher)}-{_slug(collection)}-{video_id}"
    chapters = chapters_from_yt_info(info)
    if not chapters:
        raise ValueError("no chapters in video metadata or description")

    audio_rel = "audio.wav"
    frames_dir = bundle_dir / "frames"
    scenes: list[dict[str, Any]] = []

    for ch in chapters:
        idx = int(ch["index"])
        title = str(ch["title"])
        t0 = round(float(ch["t0"]), 3)
        t1 = round(float(ch["t1"]), 3)
        slug = _slug(title)[:48] or f"chapter-{idx:02d}"
        scene_id = f"{source}-{idx:02d}-{slug}"
        row: dict[str, Any] = {
            "id": scene_id,
            "source": source,
            "publisher": publisher,
            "collection": collection,
            "video_id": video_id,
            "profile": profile,
            "chapter_index": idx,
            "chapter_title": title,
            "speaker": speaker,
            "lang": str(info.get("language") or "ru")[:2],
            "t0": t0,
            "t1": t1,
            "wav": audio_rel,
            "caption": title,
        }
        if with_frames and video_path and video_path.is_file():
            chapter_frames_dir = frames_dir / f"{idx:02d}-{slug}"
            burst = extract_chapter_burst(
                video_path,
                t0=t0,
                t1=t1,
                out_dir=frames_dir,
                chapter_index=idx,
                slug=slug,
                interval_sec=frame_interval_sec,
                min_frames=min_frames_per_chapter,
                max_frames=max_frames_per_chapter,
                scene_threshold=scene_cut_threshold,
            )
            if burst:
                row["beats"] = burst
                row["beat_mode"] = "scene_cut_paired"
                row["scene_cut_threshold"] = scene_cut_threshold
                row["frames"] = [{"id": b["id"], "t": b["t0"], "path": b["path"]} for b in burst]
                row["frame"] = burst[0]["path"]
        scenes.append(row)
    return scenes


def write_manifest(bundle_dir: Path, scenes: list[dict[str, Any]]) -> Path:
    manifest = bundle_dir / "manifest.ndjson"
    with manifest.open("w", encoding="utf-8") as fh:
        for scene in scenes:
            fh.write(json.dumps(scene, ensure_ascii=False) + "\n")
    return manifest


def rebuild_chapter_frames(
    bundle_dir: Path,
    *,
    chapter_indices: list[int] | None = None,
    video_path: Path | None = None,
    frame_interval_sec: float = 12.0,
    min_frames_per_chapter: int = 4,
    max_frames_per_chapter: int = 40,
    scene_cut_threshold: float = 0.35,
) -> dict[str, Any]:
    """Re-extract visual burst for selected chapters; rewrite manifest.ndjson."""
    bundle_dir = bundle_dir.resolve()
    manifest_path = bundle_dir / "manifest.ndjson"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    if video_path is None:
        for ext in ("mp4", "mkv", "webm"):
            candidate = bundle_dir / f"video.{ext}"
            if candidate.is_file():
                video_path = candidate
                break
    if video_path is None or not video_path.is_file():
        raise FileNotFoundError(f"no video file in {bundle_dir}")

    want = set(chapter_indices) if chapter_indices is not None else None
    scenes: list[dict[str, Any]] = []
    rebuilt = 0
    frame_total = 0

    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        idx = int(row.get("chapter_index", -1))
        if want is not None and idx not in want:
            scenes.append(row)
            continue
        t0 = float(row.get("t0") or 0.0)
        t1 = float(row.get("t1") or t0 + 1.0)
        title = str(row.get("chapter_title") or row.get("caption") or f"chapter-{idx:02d}")
        slug = _slug(title)[:48] or f"chapter-{idx:02d}"
        chapter_frames_dir = bundle_dir / "frames"
        burst = extract_chapter_burst(
            video_path,
            t0=t0,
            t1=t1,
            out_dir=chapter_frames_dir,
            chapter_index=idx,
            slug=slug,
            interval_sec=frame_interval_sec,
            min_frames=min_frames_per_chapter,
            max_frames=max_frames_per_chapter,
            scene_threshold=scene_cut_threshold,
        )
        if burst:
            row["beats"] = burst
            row["beat_mode"] = "scene_cut_paired"
            row["scene_cut_threshold"] = scene_cut_threshold
            row["frames"] = [{"id": b["id"], "t": b["t0"], "path": b["path"]} for b in burst]
            row["frame"] = burst[0]["path"]
            rebuilt += 1
            frame_total += len(burst)
        scenes.append(row)

    write_manifest(bundle_dir, scenes)
    return {
        "bundle_dir": str(bundle_dir),
        "manifest": str(manifest_path),
        "chapters_rebuilt": rebuilt,
        "frames_extracted": frame_total,
    }


def update_sources_index(corpus_root: Path, entry: dict[str, Any]) -> Path:
    index_path = corpus_root / "sources.json"
    rows: list[dict[str, Any]] = []
    if index_path.is_file():
        try:
            loaded = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                rows = [r for r in loaded if isinstance(r, dict)]
        except json.JSONDecodeError:
            rows = []
    key = str(entry.get("bundle_dir") or "")
    rows = [r for r in rows if str(r.get("bundle_dir") or "") != key]
    rows.append(entry)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index_path


def cold_path_youtube_chapters(
    url: str,
    *,
    corpus_root: Path,
    publisher: str,
    collection: str,
    speaker: str = "narrator",
    profile: str = "bind",
    fetch: bool = True,
    fetch_video: bool = True,
    with_frames: bool = True,
    frame_interval_sec: float = 12.0,
    min_frames_per_chapter: int = 4,
    max_frames_per_chapter: int = 40,
    scene_cut_threshold: float = 0.35,
) -> dict[str, Any]:
    video_id = youtube_video_id(url)
    bundle_dir = source_bundle_dir(
        corpus_root,
        publisher=publisher,
        collection=collection,
        video_id=video_id,
    )
    audio_wav: Path | None = None
    video_path: Path | None = None
    info: dict[str, Any]

    if fetch:
        fetched = fetch_youtube_bundle(url, bundle_dir, fetch_video=fetch_video)
        info = fetched["info"]
        audio_wav = fetched.get("audio_wav")
        video_path = fetched.get("video_path")
    else:
        info_path = bundle_dir / "video.info.json"
        if not info_path.is_file():
            raise FileNotFoundError(f"missing {info_path}; run with --fetch")
        info = json.loads(info_path.read_text(encoding="utf-8"))
        candidate = bundle_dir / "audio.wav"
        audio_wav = candidate if candidate.is_file() else None
        for ext in ("mp4", "mkv", "webm"):
            candidate = bundle_dir / f"video.{ext}"
            if candidate.is_file():
                video_path = candidate
                break

    scenes = build_chapter_manifest(
        bundle_dir=bundle_dir,
        info=info,
        publisher=publisher,
        collection=collection,
        speaker=speaker,
        profile=profile,
        with_frames=with_frames and fetch_video,
        video_path=video_path,
        frame_interval_sec=frame_interval_sec,
        min_frames_per_chapter=min_frames_per_chapter,
        max_frames_per_chapter=max_frames_per_chapter,
        scene_cut_threshold=scene_cut_threshold,
    )
    manifest = write_manifest(bundle_dir, scenes)
    index = update_sources_index(
        corpus_root,
        {
            "publisher": publisher,
            "collection": collection,
            "video_id": video_id,
            "title": info.get("title"),
            "url": url,
            "profile": profile,
            "bundle_dir": str(bundle_dir),
            "manifest": str(manifest),
            "scenes": len(scenes),
            "has_audio": bool(audio_wav and audio_wav.is_file()),
            "has_video": bool(video_path and video_path.is_file()),
        },
    )
    return {
        "corpus_root": str(corpus_root),
        "bundle_dir": str(bundle_dir),
        "manifest": str(manifest),
        "sources_index": str(index),
        "scenes": len(scenes),
        "title": info.get("title"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube chapters → listen bind manifest (external corpus)")
    parser.add_argument("url", help="YouTube video URL (single video, not playlist stream)")
    parser.add_argument("--corpus-root", type=Path, default=None, help="default: CASA_LISTEN_CORPUS or ../casa-listen-corpus")
    parser.add_argument("--publisher", default="lalabook", help="publisher folder, e.g. lalabook")
    parser.add_argument("--collection", default="speech-dev", help="collection folder slug")
    parser.add_argument("--speaker", default="narrator")
    parser.add_argument("--profile", default="bind", choices=("bind", "womb"))
    parser.add_argument("--no-fetch", action="store_true", help="reuse downloaded files in bundle dir")
    parser.add_argument("--audio-only", action="store_true", help="skip video download and frames")
    parser.add_argument("--no-frames", action="store_true", help="manifest without frame extraction")
    parser.add_argument("--frame-interval", type=float, default=12.0, help="seconds between burst frames (bind)")
    parser.add_argument("--max-frames-per-chapter", type=int, default=80)
    parser.add_argument("--min-frames-per-chapter", type=int, default=4)
    parser.add_argument("--scene-cut-threshold", type=float, default=0.35, help="ffmpeg gt(scene) for beat cuts")
    parser.add_argument(
        "--reburst-chapters",
        type=str,
        default="",
        help="with --no-fetch: comma chapter indices to re-extract burst only, e.g. 0 or 0,1",
    )
    args = parser.parse_args()

    root = (args.corpus_root or listen_corpus_root()).resolve()
    if args.reburst_chapters.strip():
        if not args.no_fetch:
            print("note: --reburst-chapters implies --no-fetch", file=sys.stderr)
        indices = [int(x.strip()) for x in args.reburst_chapters.split(",") if x.strip()]
        bundle_guess = source_bundle_dir(
            root,
            publisher=args.publisher,
            collection=args.collection,
            video_id=youtube_video_id(args.url),
        )
        rep = rebuild_chapter_frames(
            bundle_guess,
            chapter_indices=indices,
            frame_interval_sec=max(1.0, float(args.frame_interval)),
            min_frames_per_chapter=max(1, int(args.min_frames_per_chapter)),
            max_frames_per_chapter=max(1, int(args.max_frames_per_chapter)),
            scene_cut_threshold=max(0.05, min(0.95, float(args.scene_cut_threshold))),
        )
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    rep = cold_path_youtube_chapters(
        args.url,
        corpus_root=root,
        publisher=args.publisher,
        collection=args.collection,
        speaker=args.speaker,
        profile=args.profile,
        fetch=not args.no_fetch,
        fetch_video=not args.audio_only,
        with_frames=not args.no_frames,
        frame_interval_sec=max(1.0, float(args.frame_interval)),
        min_frames_per_chapter=max(1, int(args.min_frames_per_chapter)),
        max_frames_per_chapter=max(1, int(args.max_frames_per_chapter)),
        scene_cut_threshold=max(0.05, min(0.95, float(args.scene_cut_threshold))),
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print(
        f"\nNext: python tools/verify_listen_beats.py --manifest {rep['manifest']} "
        f"--store-dir agents/von-neumann",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
