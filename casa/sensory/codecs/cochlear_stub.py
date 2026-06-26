#!/usr/bin/env python3
"""Cochlear stub: wav → spectrum + binaural ITD/ILD (ADR-0028 v0)."""

from __future__ import annotations

import hashlib
import math

from casa.domain.auditory_imprint import AuditoryImprintPlan
from casa.domain.auditory_tract import (
    BINAURAL_ILD_LEVELS,
    BINAURAL_ITD_LEVELS,
    CODEC_COCHLEAR_STUB,
    DEFAULT_AUDIO_GRID,
    DEFAULT_ENERGY_LEVELS,
    DEFAULT_SPECTRAL_BINS,
    LATTICE_AUDIO_BINAURAL,
    LATTICE_AUDIO_SPECTRUM,
)
from casa.domain.visual_imprint import CellPlacement
from casa.sensory.load_wav import WavSlice

_ITD_CENTER = BINAURAL_ITD_LEVELS // 2
_ILD_CENTER = BINAURAL_ILD_LEVELS // 2
_MAX_ITD_LAG = 24


def _quantize01(value: float, *, levels: int) -> int:
    v = max(0.0, min(1.0, float(value)))
    lv = max(2, int(levels))
    return min(lv - 1, int(v * lv))


def _segment_rms(samples: tuple[float, ...], start: int, end: int) -> float:
    if end <= start:
        return 0.0
    acc = 0.0
    for i in range(start, end):
        s = samples[i]
        acc += s * s
    return math.sqrt(acc / max(1, end - start))


def _segment_zcr(samples: tuple[float, ...], start: int, end: int) -> float:
    if end <= start + 1:
        return 0.0
    crossings = 0
    prev = samples[start]
    for i in range(start + 1, end):
        cur = samples[i]
        if (prev >= 0.0 and cur < 0.0) or (prev < 0.0 and cur >= 0.0):
            crossings += 1
        prev = cur
    return crossings / max(1, end - start - 1)


def _segment_brightness(samples: tuple[float, ...], start: int, end: int) -> float:
    if end <= start + 1:
        return 0.0
    diff_acc = 0.0
    for i in range(start + 1, end):
        d = samples[i] - samples[i - 1]
        diff_acc += d * d
    return math.sqrt(diff_acc / max(1, end - start - 1))


def energy_token(level: int, *, channel: str | None = None) -> str:
    if channel:
        return f"A:energy:{channel}:{level:02x}"
    return f"A:energy:{level:02x}"


def bin_token(level: int, *, channel: str | None = None) -> str:
    if channel:
        return f"A:bin:{channel}:{level:02x}"
    return f"A:bin:{level:02x}"


def dyn_token(kind: str) -> str:
    return f"A:dyn:{kind}"


def pan_token(kind: str) -> str:
    return f"A:pan:{kind}"


def itd_token(quant: int) -> str:
    return f"A:itd:{quant:02x}"


def ild_token(quant: int) -> str:
    return f"A:ild:{quant:02x}"


def scene_audio_token(scene_id: str) -> str:
    return f"A:scene:{scene_id}"


def _pan_kind(left_rms: float, right_rms: float) -> str:
    total = left_rms + right_rms
    if total <= 1e-9:
        return "center"
    balance = (right_rms - left_rms) / total
    if balance > 0.25:
        return "right"
    if balance < -0.25:
        return "left"
    return "center"


def _estimate_itd_lag(
    left: tuple[float, ...],
    right: tuple[float, ...],
    start: int,
    end: int,
    *,
    max_lag: int = _MAX_ITD_LAG,
) -> int:
    seg_l = left[start:end]
    seg_r = right[start:end]
    if len(seg_l) < 4 or len(seg_r) < 4:
        return 0
    best_lag = 0
    best_corr = -1e18
    for lag in range(-max_lag, max_lag + 1):
        acc = 0.0
        count = 0
        for i, lv in enumerate(seg_l):
            j = i + lag
            if 0 <= j < len(seg_r):
                acc += lv * seg_r[j]
                count += 1
        if count <= 0:
            continue
        corr = acc / count
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag


def _quantize_itd_lag(lag: int) -> int:
    clamped = max(-_MAX_ITD_LAG, min(_MAX_ITD_LAG, int(lag)))
    span = _MAX_ITD_LAG * 2
    if span <= 0:
        return _ITD_CENTER
    norm = (clamped + _MAX_ITD_LAG) / span
    return min(BINAURAL_ITD_LEVELS - 1, int(norm * (BINAURAL_ITD_LEVELS - 1)))


def _quantize_ild_db(left_rms: float, right_rms: float) -> int:
    if left_rms <= 1e-9 and right_rms <= 1e-9:
        return _ILD_CENTER
    ratio = (right_rms + 1e-9) / (left_rms + 1e-9)
    db = max(-12.0, min(12.0, 20.0 * math.log10(ratio)))
    norm = (db + 12.0) / 24.0
    return min(BINAURAL_ILD_LEVELS - 1, int(norm * (BINAURAL_ILD_LEVELS - 1)))


def _encode_channel_contour(
    samples: tuple[float, ...],
    *,
    frames: int,
    n: int,
    channel: str | None,
    y_energy: int,
    y_dyn: int,
    y_bin_base: int,
    energy_levels: int,
    spectral_bins: int,
    placements: list[CellPlacement],
) -> list[float]:
    frame_rms: list[float] = []
    for fi in range(frames):
        start = fi * n // frames
        end = (fi + 1) * n // frames
        frame_rms.append(_segment_rms(samples, start, end))
    max_rms = max(frame_rms) if frame_rms else 1e-9
    max_rms = max(max_rms, 1e-9)
    prev_lvl: int | None = None
    for fi, rms in enumerate(frame_rms):
        norm_energy = rms / max_rms
        e_lvl = _quantize01(norm_energy, levels=energy_levels)
        placements.append(CellPlacement(x=fi, y=y_energy, token=energy_token(e_lvl, channel=channel)))
        if prev_lvl is not None:
            if e_lvl > prev_lvl:
                placements.append(CellPlacement(x=fi, y=y_dyn, token=dyn_token("rise")))
            elif e_lvl < prev_lvl:
                placements.append(CellPlacement(x=fi, y=y_dyn, token=dyn_token("fall")))
        prev_lvl = e_lvl

        start = fi * n // frames
        end = (fi + 1) * n // frames
        zcr = _segment_zcr(samples, start, end)
        bright = _segment_brightness(samples, start, end)
        b_zcr = _quantize01(min(1.0, zcr * 4.0), levels=spectral_bins)
        b_hi = _quantize01(min(1.0, bright * 12.0), levels=spectral_bins)
        placements.append(CellPlacement(x=fi, y=y_bin_base + b_zcr, token=bin_token(b_zcr, channel=channel)))
        placements.append(CellPlacement(x=fi, y=y_bin_base + 8 + b_hi, token=bin_token(b_hi, channel=channel)))
    return frame_rms


def _encode_binaural_frames(
    left: tuple[float, ...],
    right: tuple[float, ...],
    *,
    frames: int,
    n: int,
    left_rms_series: list[float],
    right_rms_series: list[float],
) -> list[CellPlacement]:
    out: list[CellPlacement] = []
    for fi in range(frames):
        start = fi * n // frames
        end = (fi + 1) * n // frames
        lag = _estimate_itd_lag(left, right, start, end)
        itd_q = _quantize_itd_lag(lag)
        ild_q = _quantize_ild_db(left_rms_series[fi], right_rms_series[fi])
        out.append(CellPlacement(x=fi, y=itd_q, token=itd_token(itd_q)))
        out.append(CellPlacement(x=fi, y=16 + ild_q, token=ild_token(ild_q)))
    return out


def encode_cochlear_stub(
    wav: WavSlice,
    *,
    window_id: str,
    scene_id: str,
    grid_size: int = DEFAULT_AUDIO_GRID,
    energy_levels: int = DEFAULT_ENERGY_LEVELS,
    spectral_bins: int = DEFAULT_SPECTRAL_BINS,
) -> AuditoryImprintPlan:
    channels = wav.channel_samples or (wav.samples,)
    n = len(channels[0]) if channels and channels[0] else 0
    spectrum_placements: list[CellPlacement] = []
    binaural_placements: list[CellPlacement] = []
    if n <= 0:
        return AuditoryImprintPlan(
            window_id=window_id,
            scene_id=scene_id,
            audio_hash="",
            codec_id=CODEC_COCHLEAR_STUB,
            grid_size=grid_size,
            sample_rate=wav.sample_rate,
            duration_ms=wav.duration_ms,
            placements_by_lattice={},
        )

    frames = max(1, min(grid_size, n // max(1, wav.sample_rate // 50)))
    use_stereo = wav.is_stereo and len(channels) >= 2
    if use_stereo:
        left = channels[0]
        right = channels[1]
        n = min(len(left), len(right))
        left_rms_series = _encode_channel_contour(
            left[:n],
            frames=frames,
            n=n,
            channel="L",
            y_energy=0,
            y_dyn=1,
            y_bin_base=2,
            energy_levels=energy_levels,
            spectral_bins=spectral_bins,
            placements=spectrum_placements,
        )
        right_rms_series = _encode_channel_contour(
            right[:n],
            frames=frames,
            n=n,
            channel="R",
            y_energy=16,
            y_dyn=17,
            y_bin_base=18,
            energy_levels=energy_levels,
            spectral_bins=spectral_bins,
            placements=spectrum_placements,
        )
        for fi, (lr, rr) in enumerate(zip(left_rms_series, right_rms_series, strict=True)):
            spectrum_placements.append(
                CellPlacement(x=fi, y=31, token=pan_token(_pan_kind(lr, rr)))
            )
        binaural_placements = _encode_binaural_frames(
            left[:n],
            right[:n],
            frames=frames,
            n=n,
            left_rms_series=left_rms_series,
            right_rms_series=right_rms_series,
        )
    else:
        mono = channels[0] if channels else wav.samples
        _encode_channel_contour(
            mono,
            frames=frames,
            n=len(mono),
            channel=None,
            y_energy=0,
            y_dyn=1,
            y_bin_base=2,
            energy_levels=energy_levels,
            spectral_bins=spectral_bins,
            placements=spectrum_placements,
        )

    anchor_x = min(frames - 1, grid_size // 2)
    spectrum_placements.append(CellPlacement(x=anchor_x, y=grid_size - 2, token=scene_audio_token(scene_id)))
    if use_stereo:
        spectrum_placements.append(CellPlacement(x=anchor_x, y=grid_size - 1, token="A:layout:stereo"))
        binaural_placements.append(CellPlacement(x=anchor_x, y=grid_size - 1, token=scene_audio_token(scene_id)))

    digest_src = channels[0][: min(64, n)]
    digest = hashlib.sha256(repr(digest_src).encode()).hexdigest()
    by_lattice = {LATTICE_AUDIO_SPECTRUM: tuple(spectrum_placements)}
    if binaural_placements:
        by_lattice[LATTICE_AUDIO_BINAURAL] = tuple(binaural_placements)
    return AuditoryImprintPlan(
        window_id=window_id,
        scene_id=scene_id,
        audio_hash=digest,
        codec_id=CODEC_COCHLEAR_STUB,
        grid_size=grid_size,
        sample_rate=wav.sample_rate,
        duration_ms=wav.duration_ms,
        placements_by_lattice=by_lattice,
    )
