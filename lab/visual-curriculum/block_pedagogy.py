"""Block moment plans — waves, train/held-out split (von Neumann RU teaching plan)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]

from literacy_pedagogy import frames_for_stage  # noqa: E402
from manifest_steps import frame_by_id, letter_frame_id, steps_for_frame  # noqa: E402
from teacher_pedagogy import load_class_manifest  # noqa: E402

_BLOCK_SPECS: dict[str, Path] = {
    "block-01-grapheme-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-01-grapheme-cyrl-v1.json",
    "block-02-meta-phonology-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-02-meta-phonology-cyrl-v1.json",
    "block-03-syllable-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-03-syllable-cyrl-v1.json",
    "block-04-early-words-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-04-early-words-cyrl-v1.json",
    "block-05-corpus-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-05-corpus-cyrl-v1.json",
    "block-06-closed-class-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-06-closed-class-cyrl-v1.json",
}


def default_block_spec_path(block_id: str) -> Path:
    path = _BLOCK_SPECS.get(block_id)
    if path is None:
        raise KeyError(f"unknown block_id: {block_id!r}")
    return path


def load_block_spec(path: Path | str | None = None, *, block_id: str = "block-01-grapheme-cyrl") -> dict[str, Any]:
    p = Path(path) if path else default_block_spec_path(block_id)
    data = json.loads(p.read_text(encoding="utf-8"))
    data["_path"] = str(p.resolve())
    data.setdefault("block_id", block_id)
    return data


def block_kind(spec: dict[str, Any]) -> str:
    if spec.get("held_out_corpus") or any(
        isinstance(w, dict) and w.get("corpus_batch") for w in (spec.get("waves") or [])
    ):
        return "corpus"
    if spec.get("held_out_frame_ids") or any(
        isinstance(w, dict) and w.get("frame_ids") for w in (spec.get("waves") or [])
    ):
        return "frames"
    return "grapheme"


def _manifest(spec: dict[str, Any]) -> dict[str, Any]:
    return load_class_manifest(str(spec.get("class_rel") or "lessons/literacy-cards"))


def _wordlist_path(spec: dict[str, Any]) -> Path | None:
    rel = spec.get("wordlist")
    return (_REPO / str(rel)).resolve() if rel else None


def held_out_cues(spec: dict[str, Any]) -> list[str]:
    return [str(c) for c in (spec.get("held_out_cues") or [])]


def corpus_frame_ids(
    spec: dict[str, Any],
    *,
    offset: int = 0,
    limit: int = 0,
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    manifest = manifest or _manifest(spec)
    stage = str(spec.get("stage_id") or "")
    frames = frames_for_stage(
        manifest,
        stage,
        limit=limit,
        offset=offset,
        order="wordlist",
        wordlist_path=_wordlist_path(spec),
    )
    return [str(f["id"]) for f in frames]


def held_out_frame_ids(spec: dict[str, Any], manifest: dict[str, Any] | None = None) -> list[str]:
    if spec.get("held_out_frame_ids"):
        return [str(fid) for fid in spec["held_out_frame_ids"]]
    held_corpus = spec.get("held_out_corpus")
    if isinstance(held_corpus, dict):
        return corpus_frame_ids(
            spec,
            offset=int(held_corpus.get("offset") or 0),
            limit=int(held_corpus.get("limit") or 0),
            manifest=manifest,
        )
    return [str(f["id"]) for f in held_out_frames(spec, manifest)]


def held_out_frames(spec: dict[str, Any], manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifest = manifest or _manifest(spec)
    if spec.get("held_out_frame_ids") or spec.get("held_out_corpus"):
        return [frame_by_id(manifest, fid) for fid in held_out_frame_ids(spec, manifest)]
    face = str(spec.get("face") or "sans")
    frames: list[dict[str, Any]] = []
    for cue in held_out_cues(spec):
        for reg in ("lower", "upper"):
            frames.append(frames_for_cue_register(manifest, cue, reg, face=face))
    return frames


def frames_for_cue_register(
    manifest: dict[str, Any],
    cue: str,
    register: str,
    *,
    face: str = "sans",
) -> dict[str, Any]:
    fid = letter_frame_id(cue, register, face=face)
    return frame_by_id(manifest, fid)


def _registers_for_wave(wave: dict[str, Any]) -> list[str]:
    return [str(r) for r in (wave.get("registers") or ["lower"])]


def _cue_register_pairs(wave: dict[str, Any]) -> list[tuple[str, str]]:
    cues = [str(c) for c in (wave.get("cues") or [])]
    registers = _registers_for_wave(wave)
    repeats = max(1, int(wave.get("repeats") or 1))
    interleave = bool(wave.get("interleave_registers"))
    pairs: list[tuple[str, str]] = []
    for _ in range(repeats):
        if interleave and len(registers) > 1:
            for cue in cues:
                for reg in registers:
                    pairs.append((cue, reg))
        else:
            for cue in cues:
                for reg in registers:
                    pairs.append((cue, reg))
    return pairs


def _frame_ids_for_wave(
    spec: dict[str, Any],
    wave: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    if wave.get("frame_ids"):
        fids = [str(fid) for fid in wave["frame_ids"]]
        repeats = max(1, int(wave.get("repeats") or 1))
        return fids * repeats
    batch = wave.get("corpus_batch")
    if isinstance(batch, dict):
        return corpus_frame_ids(
            spec,
            offset=int(batch.get("offset") or 0),
            limit=int(batch.get("limit") or 0),
            manifest=manifest,
        )
    face = str(spec.get("face") or "sans")
    out: list[str] = []
    for cue, reg in _cue_register_pairs(wave):
        out.append(letter_frame_id(cue, reg, face=face))
    return out


def wave_moment_jobs(
    spec: dict[str, Any],
    wave: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    manifest = manifest or _manifest(spec)
    prefix = str(wave.get("moment_prefix") or f"block-w{wave.get('wave', 0)}")
    jobs: list[tuple[str, list[dict[str, Any]]]] = []
    for idx, fid in enumerate(_frame_ids_for_wave(spec, wave, manifest), start=1):
        frame = frame_by_id(manifest, fid)
        mid = f"{prefix}-{fid}-{idx}"[:80]
        jobs.append((mid, steps_for_frame(frame)))
    return jobs


def all_wave_jobs(
    spec: dict[str, Any],
    *,
    waves: list[int] | None = None,
    manifest: dict[str, Any] | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    manifest = manifest or _manifest(spec)
    want = set(waves) if waves else None
    jobs: list[tuple[str, list[dict[str, Any]]]] = []
    for wave in spec.get("waves") or []:
        if not isinstance(wave, dict):
            continue
        wno = int(wave.get("wave") or 0)
        if want is not None and wno not in want:
            continue
        jobs.extend(wave_moment_jobs(spec, wave, manifest))
    return jobs


def gate_pass(spec: dict[str, Any], report: dict[str, Any]) -> bool:
    gate = (spec.get("gate") or {}).get("pass") or {}
    total = int(report.get("total") or 0)
    if total <= 0:
        return False
    know = int(report.get("know") or 0)
    empty = int(report.get("empty") or 0)
    ambiguous = int(report.get("ambiguous") or 0)
    min_ratio = float(gate.get("know_min_ratio") or 0.85)
    empty_max = int(gate.get("empty_max") if gate.get("empty_max") is not None else 0)
    amb_max_ratio = float(gate.get("ambiguous_max_ratio") or 0.1)
    if empty > empty_max:
        return False
    if know / total < min_ratio:
        return False
    if ambiguous / total > amb_max_ratio:
        return False
    return True


def train_cue_set(spec: dict[str, Any]) -> set[str]:
    held = set(held_out_cues(spec))
    out: set[str] = set()
    for wave in spec.get("waves") or []:
        if not isinstance(wave, dict):
            continue
        for cue in wave.get("cues") or []:
            c = str(cue)
            if c not in held:
                out.add(c)
    return out
