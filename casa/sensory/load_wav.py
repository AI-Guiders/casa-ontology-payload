#!/usr/bin/env python3
"""Load PCM wav slice — mono or per-channel stereo (stdlib only)."""

from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WavSlice:
    channel_samples: tuple[tuple[float, ...], ...]
    sample_rate: int
    duration_ms: int

    @property
    def channel_count(self) -> int:
        return len(self.channel_samples)

    @property
    def is_stereo(self) -> bool:
        return self.channel_count >= 2

    @property
    def samples(self) -> tuple[float, ...]:
        """Mono downmix — fallback only; encode prefers per-channel."""
        if not self.channel_samples:
            return ()
        if len(self.channel_samples) == 1:
            return self.channel_samples[0]
        n = min(len(ch) for ch in self.channel_samples)
        if n <= 0:
            return ()
        mix: list[float] = []
        for i in range(n):
            mix.append(sum(ch[i] for ch in self.channel_samples) / len(self.channel_samples))
        return tuple(mix)

    @property
    def frame_count(self) -> int:
        return len(self.samples)


def _decode_frame_ints(raw: bytes, sampwidth: int) -> list[int]:
    if sampwidth == 2:
        count = len(raw) // 2
        return list(struct.unpack(f"<{count}h", raw))
    if sampwidth == 1:
        return [b - 128 for b in raw]
    if sampwidth == 4:
        count = len(raw) // 4
        return list(struct.unpack(f"<{count}i", raw))
    raise ValueError(f"unsupported wav sampwidth: {sampwidth}")


def _normalize_sample(value: int) -> float:
    return max(-1.0, min(1.0, value / 32768.0))


def _read_pcm_channels(
    wf: wave.Wave_read,
    *,
    start_frame: int,
    end_frame: int,
) -> list[list[float]]:
    wf.setpos(max(0, start_frame))
    n_frames = max(0, end_frame - start_frame)
    raw = wf.readframes(n_frames)
    if not raw:
        return []
    sampwidth = wf.getsampwidth()
    n_channels = wf.getnchannels()
    ints = _decode_frame_ints(raw, sampwidth)
    channels: list[list[float]] = [[] for _ in range(n_channels)]
    for i in range(0, len(ints), n_channels):
        chunk = ints[i : i + n_channels]
        if not chunk:
            continue
        for ch_idx, sample in enumerate(chunk):
            if ch_idx < n_channels:
                channels[ch_idx].append(_normalize_sample(sample))
    return channels


def load_wav_slice(
    path: Path | str,
    *,
    t0_sec: float | None = None,
    t1_sec: float | None = None,
) -> WavSlice:
    path = Path(path)
    with wave.open(str(path), "rb") as wf:
        sample_rate = int(wf.getframerate())
        n_frames = int(wf.getnframes())
        start = 0 if t0_sec is None else max(0, int(t0_sec * sample_rate))
        end = n_frames if t1_sec is None else min(n_frames, int(t1_sec * sample_rate))
        if end <= start:
            end = min(n_frames, start + max(1, sample_rate // 10))
        channels = _read_pcm_channels(wf, start_frame=start, end_frame=end)
    if not channels:
        channel_tuple: tuple[tuple[float, ...], ...] = ()
    else:
        channel_tuple = tuple(tuple(ch) for ch in channels)
    frame_len = len(channel_tuple[0]) if channel_tuple else 0
    duration_ms = int(1000 * frame_len / max(1, sample_rate))
    return WavSlice(
        channel_samples=channel_tuple,
        sample_rate=sample_rate,
        duration_ms=duration_ms,
    )


def write_synthetic_contour_wav(
    path: Path | str,
    *,
    sample_rate: int = 16_000,
    duration_sec: float = 0.48,
    base_freq: float = 220.0,
    stereo: bool = False,
    pan: float = 0.0,
) -> WavSlice:
    """Sine with rising envelope. stereo=True keeps L/R separate (pan -1..1)."""
    path = Path(path)
    n = max(1, int(sample_rate * duration_sec))
    mono: list[float] = []
    for i in range(n):
        t = i / sample_rate
        env = 0.15 + 0.85 * (i / max(1, n - 1))
        mono.append(env * math.sin(2.0 * math.pi * base_freq * t))

    if not stereo:
        ints = [max(-32768, min(32767, int(s * 32767))) for s in mono]
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{len(ints)}h", *ints))
        return WavSlice(
            channel_samples=(tuple(mono),),
            sample_rate=sample_rate,
            duration_ms=int(1000 * duration_sec),
        )

    pan = max(-1.0, min(1.0, float(pan)))
    left_gain = math.sqrt(0.5 * (1.0 - pan))
    right_gain = math.sqrt(0.5 * (1.0 + pan))
    left: list[int] = []
    right: list[int] = []
    for s in mono:
        left.append(max(-32768, min(32767, int(s * left_gain * 32767))))
        right.append(max(-32768, min(32767, int(s * right_gain * 32767))))
    interleaved: list[int] = []
    for lv, rv in zip(left, right, strict=True):
        interleaved.extend([lv, rv])
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(interleaved)}h", *interleaved))
    left_f = tuple(v / 32768.0 for v in left)
    right_f = tuple(v / 32768.0 for v in right)
    return WavSlice(
        channel_samples=(left_f, right_f),
        sample_rate=sample_rate,
        duration_ms=int(1000 * duration_sec),
    )
