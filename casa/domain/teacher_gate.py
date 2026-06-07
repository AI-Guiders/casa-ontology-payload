#!/usr/bin/env python3
"""Teacher probe registry — gate kind + pass criteria (CASA teacher framework / ADR-0037).

Honest KSA (knowledge / skills / abilities) probes credit mastery on agent store; sidecar spec regression does not.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from dataclasses import dataclass


class GateKind(str, Enum):
    AGENT_KSA = "agent_ksa"
    SIDECAR_SPEC = "sidecar_spec"


@dataclass(frozen=True, slots=True)
class ProbeSpec:
    kind: GateKind
    description: str = ""


# Explicit registry — unknown probes default via infer_gate_kind (safe: no mastery credit).
PROBE_REGISTRY: dict[str, ProbeSpec] = {
    # Gate = knowledge / skills / abilities on agent field (held-out + store)
    "literacy-corpus-quiz": ProbeSpec(GateKind.AGENT_KSA, "whole-word corpus held-out"),
    "literacy-quiz": ProbeSpec(GateKind.AGENT_KSA, "grapheme pilot frames"),
    "literacy-closed-class-quiz": ProbeSpec(GateKind.AGENT_KSA, "closed-class words"),
    "analytic-read-corpus-r1": ProbeSpec(GateKind.AGENT_KSA, "R1 analytic read on store"),
    "phrase-compose-pilot": ProbeSpec(GateKind.AGENT_KSA, "phrase compose single event on store"),
    "phrase-agent-store": ProbeSpec(GateKind.AGENT_KSA, "phrase batch held-out on agent store"),
    "paradigm-select": ProbeSpec(GateKind.AGENT_KSA, "pilot paradigm forms known in agent LTM"),
    "syllable-cyrl-quiz": ProbeSpec(GateKind.AGENT_KSA, "syllable frames"),
    "meta-phonology-quiz": ProbeSpec(GateKind.AGENT_KSA, "phonology meta category"),
    "meta-pure-quiz": ProbeSpec(GateKind.AGENT_KSA, "meta language pure cards"),
    "probe_lexical_read_fluent_ru": ProbeSpec(GateKind.AGENT_KSA, "whole-word fluent read held-out"),
    "probe_block01_grapheme_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 1 held-out grapheme gate"),
    "probe_block02_meta_phonology_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 2 meta-phonology held-out"),
    "probe_block03_syllable_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 3 syllable held-out"),
    "probe_block04_early_words_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 4 early whole-word held-out"),
    "probe_block05_corpus_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 5 corpus held-out 20%"),
    "probe_block06_closed_class_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 6 closed-class held-out"),
    "probe_block06b_meta_language_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 6b meta-language held-out"),
    "probe_block07_grammar_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 7 grammar person/case held-out"),
    "probe_block08_grammar_phrase_meta_held_out": ProbeSpec(
        GateKind.AGENT_KSA, "block 8 agreement/possessive/numeral meta held-out"
    ),
    "probe_passage_comprehend_ru_v0": ProbeSpec(GateKind.AGENT_KSA, "passage comprehension held-out"),
    "probe_morphemics_ru_v0": ProbeSpec(GateKind.AGENT_KSA, "morphemics segment bind held-out"),
    "probe_block09c_morphemics_held_out": ProbeSpec(GateKind.AGENT_KSA, "block 9c morphemics held-out"),
    "probe_oov_word_recall_v0": ProbeSpec(GateKind.AGENT_KSA, "OOV remember recall"),
    "probe_orthography_ru_v0": ProbeSpec(GateKind.AGENT_KSA, "orthography in context"),
    "probe_grammar_punct_ru_v0": ProbeSpec(GateKind.AGENT_KSA, "punctuation in context"),
    "nline-compare-quiz": ProbeSpec(GateKind.AGENT_KSA, "numberline compare"),
    "venn-region-quiz": ProbeSpec(GateKind.AGENT_KSA, "venn region math"),
    "geom-lex-quiz": ProbeSpec(GateKind.AGENT_KSA, "geometry lex on field"),
    # Sidecar — curriculum / rule lint, synthetic reads, lab experiments
    "possessive-pilot": ProbeSpec(GateKind.SIDECAR_SPEC, "possessive events + rule compose"),
    "possessive-rule": ProbeSpec(GateKind.SIDECAR_SPEC, "possessive gender×number table"),
    "numeral-pilot": ProbeSpec(GateKind.SIDECAR_SPEC, "numeral events + rule compose"),
    "numeral-rule": ProbeSpec(GateKind.SIDECAR_SPEC, "numeral class one/few/many table"),
    "phrase-permutation-equiv": ProbeSpec(GateKind.SIDECAR_SPEC, "phrase surface permutations"),
    "phrase-case-frames": ProbeSpec(GateKind.SIDECAR_SPEC, "case via question-frames"),
    "question-frame-pilot": ProbeSpec(GateKind.SIDECAR_SPEC, "question slot frames"),
    "meta-grammar-person": ProbeSpec(GateKind.SIDECAR_SPEC, "L2 person meta registry"),
    "meta-grammar-case": ProbeSpec(GateKind.SIDECAR_SPEC, "L2 case meta registry"),
    "meta-grammar-agreement": ProbeSpec(GateKind.SIDECAR_SPEC, "L2 agreement meta registry"),
    "font-legibility-sweep": ProbeSpec(GateKind.SIDECAR_SPEC, "font pt sweep experiment"),
    "word-recognition-modes": ProbeSpec(GateKind.SIDECAR_SPEC, "L1/L2/L3 recognition experiment"),
    "math-palochki-bundle": ProbeSpec(GateKind.SIDECAR_SPEC, "math bundle cue lint"),
}


def register_stage_probe(class_id: str, stage_id: str) -> ProbeSpec:
    """Per-stage agent KSA probes ({class_id}:{stage_id})."""
    pid = f"{class_id}:{stage_id}"
    if pid not in PROBE_REGISTRY:
        PROBE_REGISTRY[pid] = ProbeSpec(GateKind.AGENT_KSA, f"stage gate {class_id} {stage_id}")
    return PROBE_REGISTRY[pid]


_SIDECAR_PREFIXES = ("meta-grammar-", "teacher-")


def infer_gate_kind(probe_id: str, report: dict[str, Any] | None = None) -> GateKind:
    """Default unknown probes to sidecar unless report clearly used agent store."""
    pid = str(probe_id or "").strip()
    if not pid:
        return GateKind.SIDECAR_SPEC
    if pid.startswith(_SIDECAR_PREFIXES):
        return GateKind.SIDECAR_SPEC
    rep = report or {}
    if rep.get("store_id") and (rep.get("items") or int(rep.get("total") or 0) > 0):
        return GateKind.AGENT_KSA
    return GateKind.SIDECAR_SPEC


def gate_kind_for_probe(probe_id: str, report: dict[str, Any] | None = None) -> GateKind:
    pid = str(probe_id or "").strip()
    spec = PROBE_REGISTRY.get(pid)
    if spec is not None:
        return spec.kind
    return infer_gate_kind(pid, report)


def credits_mastery(kind: GateKind) -> bool:
    return kind is GateKind.AGENT_KSA


def _gate_corpus_whole(report: dict[str, Any]) -> bool:
    total = int(report.get("total") or 0)
    if total <= 0:
        return False
    know = int(report.get("know") or 0)
    empty = int(report.get("empty") or 0)
    wrong = int(report.get("wrong") or 0)
    return know == total and empty == 0 and wrong == 0


def _gate_analytic_r1(report: dict[str, Any]) -> bool:
    items = report.get("items") or []
    if not items:
        return False
    ok = 0
    for row in items:
        v = str(row.get("verdict") or "")
        if v == "analytic_know":
            ok += 1
            continue
        if row.get("r1_novel_bind") and str(row.get("r1_novel_via") or "") in (
            "novel_compose",
            "corpus_align",
        ):
            ok += 1
    return ok == len(items)


def _gate_stage_full_know(report: dict[str, Any]) -> bool:
    total = int(report.get("total") or 0)
    know = int(report.get("know") or 0)
    return total > 0 and know == total and int(report.get("empty") or 0) == 0


def _gate_phrase_compose(report: dict[str, Any]) -> bool:
    if not report.get("phrase_know"):
        return False
    total_words = int(report.get("total_words") or 0)
    know_words = int(report.get("know_words") or 0)
    if total_words > 0 and know_words < total_words:
        return False
    return True


def _gate_sidecar_spec(report: dict[str, Any]) -> bool:
    if "pass" in report:
        return bool(report.get("pass"))
    for key in ("phrase_know", "permutation_know", "question_know", "case_know"):
        if key in report:
            return bool(report.get(key))
    total = int(report.get("total") or 0)
    know = int(report.get("know") or 0)
    if total > 0:
        return know == total
    return False


def _gate_phrase_agent_store(report: dict[str, Any]) -> bool:
    events = report.get("events") or []
    if not events:
        return False
    return all(_gate_phrase_compose(ev) for ev in events)


def _gate_paradigm_select(report: dict[str, Any]) -> bool:
    return bool(report.get("paradigm_select"))


def probe_gate_passed(report: dict[str, Any], gate_id: str = "") -> bool:
    """Probe verdict — independent of mastery credit (see credits_mastery + record path)."""
    probe = str(report.get("probe") or gate_id)
    kind = gate_kind_for_probe(probe, report)
    if kind is GateKind.SIDECAR_SPEC:
        return _gate_sidecar_spec(report)

    stage = str(report.get("stage") or "")
    if probe == "analytic-read-corpus-r1":
        return _gate_analytic_r1(report)
    if probe in ("literacy-corpus-quiz", "probe_lexical_read_fluent_ru") or stage == "stage-06-words-cyrl-corpus":
        return _gate_corpus_whole(report)
    if probe == "phrase-compose-pilot":
        return _gate_phrase_compose(report)
    if probe == "phrase-agent-store":
        return _gate_phrase_agent_store(report)
    if probe == "paradigm-select":
        return _gate_paradigm_select(report)
    if probe in ("probe_orthography_ru_v0", "probe_grammar_punct_ru_v0"):
        return int(report.get("know") or 0) == int(report.get("total") or 0) and int(report.get("total") or 0) > 0
    if ":" in probe and report.get("class_id"):
        return _gate_stage_full_know(report)
    if "total" in report and int(report.get("total") or 0) > 0:
        return _gate_stage_full_know(report)
    return bool(report.get("items") and _gate_analytic_r1(report))


def annotate_sidecar_report(report: dict[str, Any]) -> dict[str, Any]:
    """Mark sidecar regression report — no mastery side effects."""
    probe = str(report.get("probe") or "")
    kind = gate_kind_for_probe(probe, report)
    out = dict(report)
    out["gate_kind"] = kind.value
    out["credits_mastery"] = credits_mastery(kind)
    out["verdict_pass"] = probe_gate_passed(out, probe)
    return out
