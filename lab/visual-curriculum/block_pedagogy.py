"""Block moment plans — waves, train/held-out split (von Neumann RU teaching plan)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]

from literacy_pedagogy import frames_for_stage  # noqa: E402
from manifest_steps import (  # noqa: E402
    frame_by_id,
    letter_frame_id,
    steps_for_frame,
    steps_morph_segment_bind,
    steps_register_bind,
)
from teacher_pedagogy import load_class_manifest  # noqa: E402

_BLOCK_SPECS: dict[str, Path] = {
    "block-01-grapheme-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-01-grapheme-cyrl-v1.json",
    "block-02-meta-phonology-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-02-meta-phonology-cyrl-v1.json",
    "block-03-syllable-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-03-syllable-cyrl-v1.json",
    "block-04-early-words-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-04-early-words-cyrl-v1.json",
    "block-05-corpus-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-05-corpus-cyrl-v1.json",
    "block-06-closed-class-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-06-closed-class-cyrl-v1.json",
    "block-06b-meta-language-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-06b-meta-language-cyrl-v1.json",
    "block-07-grammar-person-case-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-07-grammar-person-case-cyrl-v1.json",
    "block-08-grammar-phrase-meta-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-08-grammar-phrase-meta-cyrl-v1.json",
    "block-09-phrase-exit-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-09-phrase-exit-cyrl-v1.json",
    "block-07c-register-bind-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-07c-register-bind-cyrl-v1.json",
    "block-08b-question-meta-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-08b-question-meta-cyrl-v1.json",
    "block-09c-morphemics-cyrl": _REPO / "lessons" / "literacy-cards" / "data" / "block-09c-morphemics-cyrl-v1.json",
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
    explicit = str(spec.get("kind") or "").strip().lower()
    if explicit in ("phrase", "corpus", "frames", "grapheme"):
        return explicit
    if spec.get("held_out_event_ids") or any(
        isinstance(w, dict) and w.get("event_ids") for w in (spec.get("waves") or [])
    ):
        return "phrase"
    if spec.get("held_out_corpus") or any(
        isinstance(w, dict) and w.get("corpus_batch") for w in (spec.get("waves") or [])
    ):
        return "corpus"
    if spec.get("held_out_frame_ids") or any(
        isinstance(w, dict) and w.get("frame_ids") for w in (spec.get("waves") or [])
    ):
        return "frames"
    return "grapheme"


def phrase_events_path(spec: dict[str, Any]) -> Path:
    rel = str(
        spec.get("events_path")
        or "lessons/literacy-cards/data/literacy/phrase-events-ru-pilot-v1.json"
    )
    return (_REPO / rel).resolve()


def phrase_wave_event_ids(
    spec: dict[str, Any],
    *,
    waves: list[int] | None = None,
) -> list[str]:
    want = set(waves) if waves else None
    out: list[str] = []
    for wave in spec.get("waves") or []:
        if not isinstance(wave, dict):
            continue
        wno = int(wave.get("wave") or 0)
        if want is not None and wno not in want:
            continue
        for eid in wave.get("event_ids") or []:
            eid = str(eid)
            if eid not in out:
                out.append(eid)
    return out


def held_out_phrase_event_ids(spec: dict[str, Any]) -> list[str]:
    return [str(e) for e in (spec.get("held_out_event_ids") or [])]


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
    morph_binds = wave.get("morph_binds") or []
    if morph_binds:
        repeats = max(1, int(wave.get("repeats") or 1))
        for r in range(repeats):
            for bi, bind in enumerate(morph_binds, start=1):
                if not isinstance(bind, dict):
                    continue
                role_fid = str(bind.get("role_frame_id") or "")
                seg_fid = str(bind.get("segment_frame_id") or "")
                phrase_fid = str(bind.get("phrase_frame_id") or "") or None
                mid = f"{prefix}-morph-{role_fid}-{r}-{bi}"[:80]
                jobs.append(
                    (
                        mid,
                        steps_morph_segment_bind(
                            manifest,
                            role_frame_id=role_fid,
                            segment_frame_id=seg_fid,
                            phrase_frame_id=phrase_fid,
                        ),
                    )
                )
        return jobs
    binds = wave.get("register_binds") or []
    if binds:
        repeats = max(1, int(wave.get("repeats") or 1))
        for r in range(repeats):
            for bi, bind in enumerate(binds, start=1):
                if not isinstance(bind, dict):
                    continue
                lower_fid = str(bind.get("lower_frame_id") or "")
                cap_fid = str(bind.get("cap_frame_id") or "")
                meta_fid = str(bind.get("meta_frame_id") or "") or None
                mid = f"{prefix}-bind-{lower_fid}-{r}-{bi}"[:80]
                jobs.append(
                    (
                        mid,
                        steps_register_bind(
                            manifest,
                            lower_frame_id=lower_fid,
                            cap_frame_id=cap_fid,
                            meta_frame_id=meta_fid,
                        ),
                    )
                )
        return jobs
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


def gate_pass_phrase(spec: dict[str, Any], report: dict[str, Any]) -> bool:
    gate = (spec.get("gate") or {}).get("pass") or {}
    if gate.get("phrase_know") is True:
        return bool(report.get("phrase_know"))
    total = int(report.get("total_events") or report.get("total") or 0)
    if total <= 0:
        return False
    know = int(report.get("phrase_know_count") or report.get("know") or 0)
    min_ratio = float(gate.get("phrase_know_min_ratio") or 1.0)
    return know / total >= min_ratio


def _meta_bridge(state: dict[str, Any], lats: dict, src: str, dst: str) -> bool:
    from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
    from casa.prisms.visual.bridge_math import DEFAULT_RELATION, bridge_exists_on_field

    src = canonical_lex_concept_id(src)
    dst = canonical_lex_concept_id(dst)
    return bridge_exists_on_field(
        lats, src=src, relation=DEFAULT_RELATION, dst=dst, state=state
    ) or bridge_exists_on_field(lats, src=dst, relation=DEFAULT_RELATION, dst=src, state=state)


def morph_segment_bind_report(
    state: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    from casa.prisms.memory.memory_prisms import memory_lattices

    lats = memory_lattices(state)
    rows: list[dict[str, Any]] = []
    ok = 0
    for row in rules:
        role = str(row.get("role_cid") or "").strip()
        segment = str(row.get("segment_cid") or "").strip()
        linked = bool(role and segment) and _meta_bridge(state, lats, role, segment)
        if linked:
            ok += 1
        rows.append({"role_cid": role, "segment_cid": segment, "linked": linked})
    return {"ok": ok, "total": len(rows), "rows": rows}


def register_meta_bind_report(
    state: dict[str, Any],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    from casa.prisms.memory.memory_prisms import memory_lattices

    lats = memory_lattices(state)
    rows: list[dict[str, Any]] = []
    ok = 0
    for row in rules:
        rule = str(row.get("rule_cid") or "").strip()
        lemma = str(row.get("lemma_cid") or "").strip()
        cap = str(row.get("cap_cid") or "").strip()
        lemma_rule = bool(lemma and rule) and _meta_bridge(state, lats, lemma, rule)
        cap_rule = bool(cap and rule) and _meta_bridge(state, lats, cap, rule)
        linked = lemma_rule and cap_rule
        if linked:
            ok += 1
        rows.append(
            {
                "rule_cid": rule,
                "lemma_cid": lemma,
                "cap_cid": cap,
                "lemma_rule": lemma_rule,
                "cap_rule": cap_rule,
                "linked": linked,
            }
        )
    return {"ok": ok, "total": len(rows), "rules": rows}


def register_bind_report(
    state: dict[str, Any],
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Legacy lex↔lex register pairs (bootstrap); prefer register_meta_bind_report."""
    from casa.prisms.memory.memory_prisms import memory_lattices

    lats = memory_lattices(state)
    rows: list[dict[str, Any]] = []
    ok = 0
    for row in pairs:
        lo = str(row.get("lower_cid") or "").strip()
        cap = str(row.get("cap_cid") or "").strip()
        linked = bool(lo and cap) and _meta_bridge(state, lats, lo, cap)
        if linked:
            ok += 1
        rows.append({"lower_cid": lo, "cap_cid": cap, "linked": linked})
    return {"ok": ok, "total": len(rows), "pairs": rows}


def gate_pass(spec: dict[str, Any], report: dict[str, Any]) -> bool:
    if block_kind(spec) == "phrase":
        return gate_pass_phrase(spec, report)
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
    meta_rules = spec.get("register_meta_rules") or []
    pairs = spec.get("register_bind_pairs") or []
    pair_lemmas: set[str] = set()
    for p in meta_rules:
        if not isinstance(p, dict):
            continue
        for key in ("lemma_cid", "cap_cid"):
            cid = str(p.get(key) or "").strip()
            if cid:
                pair_lemmas.add(cid)
    if pairs:
        for p in pairs:
            if not isinstance(p, dict):
                continue
            lo = str(p.get("lower_cid") or "").strip()
            cap = str(p.get("cap_cid") or "").strip()
            if lo:
                pair_lemmas.add(lo)
            if cap:
                pair_lemmas.add(cap)
    register_ambiguous = 0
    if gate.get("register_ambiguous_ok") and pair_lemmas:
        for item in report.get("items") or []:
            if str(item.get("verdict") or "") != "ambiguous":
                continue
            leaders = {str(x) for x in (item.get("leaders") or [])}
            if leaders and leaders <= pair_lemmas:
                register_ambiguous += 1
    effective_know = know + register_ambiguous
    residual_ambiguous = ambiguous - register_ambiguous
    if empty > empty_max:
        return False
    if effective_know / total < min_ratio:
        return False
    if residual_ambiguous / total > amb_max_ratio:
        return False
    meta_min = gate.get("register_meta_bind_min")
    if meta_min is not None and meta_rules:
        rb = report.get("register_meta_bind") or {}
        if int(rb.get("ok") or 0) < int(meta_min):
            return False
    bind_min = gate.get("register_bind_min")
    if bind_min is not None and pairs:
        rb = report.get("register_bind") or {}
        if int(rb.get("ok") or 0) < int(bind_min):
            return False
    morph_rules = spec.get("morph_meta_rules") or []
    morph_min = gate.get("morph_segment_bind_min")
    if morph_min is not None and morph_rules:
        mb = report.get("morph_segment_bind") or {}
        if int(mb.get("ok") or 0) < int(morph_min):
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
