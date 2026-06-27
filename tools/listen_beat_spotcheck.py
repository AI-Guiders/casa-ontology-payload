#!/usr/bin/env python3
"""Spot-check manifest beats against wav energy + frame files (pre-probe gate)."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Warm import chain (listen_corpus ↔ listen_beat_model cycle) before verify.
import casa.domain.listen_womb_tick  # noqa: F401

from casa.domain.listen_beat_lookup import resolve_beat_id_at_t_rel
from casa.domain.listen_beat_verify import format_beat_report, validate_scene_beats


def _rms_bins(wav_path: Path, *, bin_sec: float = 0.5, chapter_t0: float = 0.0) -> list[tuple[float, float]]:
    """Return (t_rel, rms) per bin from mono/stereo PCM wav."""
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        width = wf.getsampwidth()
        channels = wf.getnchannels()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
    if width not in (1, 2, 4):
        raise ValueError(f"unsupported sample width {width}")
    fmt = {1: "b", 2: "h", 4: "i"}[width]
    step = max(1, int(rate * bin_sec))
    samples: list[int] = []
    frame_size = width * channels
    for i in range(0, len(raw), frame_size):
        chunk = raw[i : i + frame_size]
        if len(chunk) < frame_size:
            break
        vals = struct.unpack("<" + fmt * channels, chunk)
        mono = sum(vals) / channels
        samples.append(int(mono))
    bins: list[tuple[float, float]] = []
    for start in range(0, len(samples), step):
        block = samples[start : start + step]
        if not block:
            break
        mean_sq = sum(x * x for x in block) / len(block)
        t_rel = chapter_t0 + start / rate
        bins.append((round(t_rel, 3), math.sqrt(mean_sq)))
    return bins


def _peak_window(bins: list[tuple[float, float]], t0: float, t1: float) -> tuple[float, float]:
    in_win = [(t, r) for t, r in bins if t0 <= t <= t1 + 1e-6]
    if not in_win:
        return t0, 0.0
    t_peak, r_peak = max(in_win, key=lambda x: x[1])
    return t_peak, r_peak


def _boundary_lookup_report(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scene = {"beats": beats}
    for b in beats[1:]:
        t = float(b["t0"])
        rows.append({"t_rel": t, "lookup": resolve_beat_id_at_t_rel(scene, t), "expected": b.get("id")})
    return rows


def spotcheck_beats(
    bundle_dir: Path,
    scene: dict[str, Any],
    beat_ids: list[str],
    *,
    context_sec: float = 2.0,
    bin_sec: float = 0.5,
) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    chapter_t0 = float(scene.get("t0") or 0.0)
    wav_path = bundle_dir / str(scene.get("wav") or "audio.wav")
    beats = scene.get("beats") or []
    by_id = {str(b.get("id")): b for b in beats if b.get("id")}

    out: dict[str, Any] = {
        "scene_id": scene.get("id"),
        "chapter_index": scene.get("chapter_index"),
        "beat_source": scene.get("beat_source"),
        "wav": str(wav_path),
        "structural_gate": None,
        "boundary_lookup": _boundary_lookup_report(beats),
        "beats": [],
    }

    check = validate_scene_beats(scene, bundle_dir)
    out["structural_gate"] = {"ok": check.ok, "errors": check.errors, "warnings": check.warnings}

    bins: list[tuple[float, float]] = []
    if wav_path.is_file():
        bins = _rms_bins(wav_path, bin_sec=bin_sec, chapter_t0=0.0)
        # bins use absolute timeline; convert to chapter-relative for scene beats
        bins = [(round(t - chapter_t0, 3), r) for t, r in bins if t >= chapter_t0 - 1e-6]

    for bid in beat_ids:
        beat = by_id.get(bid)
        if not beat:
            out["beats"].append({"beat_id": bid, "error": "not in manifest"})
            continue
        t0, t1 = float(beat["t0"]), float(beat["t1"])
        peak_t, peak_r = _peak_window(bins, t0, t1) if bins else (t0, 0.0)
        ctx_t0, ctx_t1 = max(0.0, t0 - context_sec), t1 + context_sec
        ctx_peak_t, ctx_peak_r = _peak_window(bins, ctx_t0, ctx_t1) if bins else (t0, 0.0)
        frame_ok = True
        frames: list[dict[str, Any]] = []
        path_ref = str(beat.get("path") or "")
        if path_ref:
            frames.append({"kind": "paired", "path": path_ref, "exists": (bundle_dir / path_ref).is_file()})
        for kf in beat.get("keyframes") or []:
            kp = str(kf.get("path") or "")
            ft = kf.get("frame_t")
            exists = (bundle_dir / kp).is_file() if kp else False
            frame_ok = frame_ok and exists
            frames.append(
                {
                    "kind": "keyframe",
                    "path": kp,
                    "frame_t": ft,
                    "exists": exists,
                    "note": (kf.get("note") or "")[:80],
                }
            )
        peak_in_window = t0 <= peak_t <= t1 + 1e-6
        peak_offset = round(peak_t - (t0 + t1) / 2, 2)
        out["beats"].append(
            {
                "beat_id": bid,
                "t0": t0,
                "t1": t1,
                "dur": round(t1 - t0, 2),
                "note": (beat.get("note") or "")[:120],
                "frames": frames,
                "audio_rms_peak_in_window": {"t_rel": peak_t, "rms": round(peak_r, 1), "in_window": peak_in_window},
                "audio_rms_peak_context": {
                    "window": [ctx_t0, ctx_t1],
                    "t_rel": ctx_peak_t,
                    "rms": round(ctx_peak_r, 1),
                    "offset_from_beat_mid_sec": round(ctx_peak_t - (t0 + t1) / 2, 2),
                },
                "lookup_at_t0": resolve_beat_id_at_t_rel(scene, t0),
                "lookup_at_mid": resolve_beat_id_at_t_rel(scene, (t0 + t1) / 2),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Spot-check listen beats vs wav + frames")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chapter", type=int, default=0)
    parser.add_argument("--beats", type=str, default="b004,b029")
    parser.add_argument("--context-sec", type=float, default=2.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    bundle_dir = manifest.parent
    scenes = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    scene = next(s for s in scenes if int(s.get("chapter_index", -1)) == args.chapter)
    beat_ids = [x.strip() for x in args.beats.split(",") if x.strip()]

    report = spotcheck_beats(bundle_dir, scene, beat_ids, context_sec=args.context_sec)
    check = validate_scene_beats(scene, bundle_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(format_beat_report(check, scene_title=str(scene.get("chapter_title") or "")))
    print()
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    bad_boundary = [r for r in report["boundary_lookup"] if r["lookup"] != r["expected"]]
    if bad_boundary:
        print("\nWARN boundary lookup mismatches:", bad_boundary[:5], file=sys.stderr)
    return 0 if check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
