#!/usr/bin/env python3
"""Vis frame id grammar — parse/build (word-, phrase-probe-, analytic-probe-, …)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from casa.prisms.visual.bridge_math import VIS_CUE_PREFIX, frame_id_from_vis_cue, vis_cue_from_frame_id

Face = Literal["sans"]


class FrameKind(str, Enum):
    WORD = "word"
    SYLLABLE = "syllable"
    PHRASE_PROBE = "phrase_probe"
    ANALYTIC_PROBE = "analytic_probe"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FrameRef:
    kind: FrameKind
    slug: str
    face: Face
    raw: str

    @property
    def frame_id(self) -> str:
        return self.raw

    @property
    def vis_cue(self) -> str:
        return vis_cue_from_frame_id(self.raw)


def _parse_bare_frame_id(fid: str) -> FrameRef | None:
    s = str(fid or "").strip()
    if not s:
        return None
    face: Face = "sans"
    body = s
    if s.endswith("-sans"):
        body = s[: -len("-sans")]
        face = "sans"
    if body.startswith("phrase-probe-"):
        slug = body[len("phrase-probe-") :]
        return FrameRef(FrameKind.PHRASE_PROBE, slug, face, s)
    if body.startswith("analytic-probe-"):
        slug = body[len("analytic-probe-") :]
        return FrameRef(FrameKind.ANALYTIC_PROBE, slug, face, s)
    if body.startswith("word-"):
        slug = body[len("word-") :]
        return FrameRef(FrameKind.WORD, slug, face, s)
    if body.startswith("syllable-"):
        slug = body[len("syllable-") :]
        return FrameRef(FrameKind.SYLLABLE, slug, face, s)
    return FrameRef(FrameKind.UNKNOWN, body, face, s)


def parse_frame_ref(cue_or_frame_id: str) -> FrameRef | None:
    fid = frame_id_from_vis_cue(cue_or_frame_id)
    return _parse_bare_frame_id(fid)


def slug_from_frame(cue_or_frame_id: str) -> str | None:
    ref = parse_frame_ref(cue_or_frame_id)
    if ref is None or ref.kind in (FrameKind.UNKNOWN, FrameKind.SYLLABLE):
        return None
    return ref.slug or None


def word_frame_id(slug: str, *, face: Face = "sans") -> str:
    return f"word-{slug}-{face}"


def syllable_frame_id(surface: str, *, face: Face = "sans") -> str:
    return f"syllable-{surface}-{face}"


def phrase_probe_frame_id(slug: str, *, face: Face = "sans") -> str:
    return f"phrase-probe-{slug}-{face}"


def analytic_probe_frame_id(slug: str, *, face: Face = "sans") -> str:
    return f"analytic-probe-{slug}-{face}"


def is_read_frame(cue_or_frame_id: str) -> bool:
    ref = parse_frame_ref(cue_or_frame_id)
    return ref is not None and ref.kind in (
        FrameKind.WORD,
        FrameKind.PHRASE_PROBE,
        FrameKind.ANALYTIC_PROBE,
        FrameKind.SYLLABLE,
    )


__all__ = [
    "VIS_CUE_PREFIX",
    "Face",
    "FrameKind",
    "FrameRef",
    "analytic_probe_frame_id",
    "frame_id_from_vis_cue",
    "is_read_frame",
    "parse_frame_ref",
    "phrase_probe_frame_id",
    "slug_from_frame",
    "syllable_frame_id",
    "vis_cue_from_frame_id",
    "word_frame_id",
]
