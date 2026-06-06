#!/usr/bin/env python3
"""Teacher framework — stage → probe wiring for all lesson classes (ADR-0037)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from casa.domain.teacher_gate import GateKind, gate_kind_for_probe

_CURRICULUM = Path(__file__).resolve().parent
_REPO = _CURRICULUM.parents[1]

ClassRel = Literal[
    "lessons/literacy-cards",
    "lessons/visual-cards",
    "lessons/lexical-cards-ru",
    "lessons/math-palochki",
]


@dataclass(frozen=True, slots=True)
class StageProbeSpec:
    """How to verify a curriculum stage after ingest."""

    script: str
    gate_kind: GateKind
    probe_id: str = ""
    extra_args: tuple[str, ...] = field(default_factory=tuple)
    uses_generic_stage: bool = False
    reinforce_tail: bool = True


def class_manifest_path(class_rel: str) -> Path:
    return (_REPO / class_rel / "class.manifest.json").resolve()


def load_class_manifest(class_rel: str) -> dict[str, Any]:
    return json.loads(class_manifest_path(class_rel).read_text(encoding="utf-8"))


def stage_probe_id(class_id: str, stage_id: str) -> str:
    return f"{class_id}:{stage_id}"


def generic_stage_probe(class_rel: str, stage_id: str) -> StageProbeSpec:
    manifest = load_class_manifest(class_rel)
    cid = str(manifest.get("class_id") or Path(class_rel).name)
    from casa.domain.teacher_gate import register_stage_probe

    register_stage_probe(cid, stage_id)
    return StageProbeSpec(
        script="probe_stage_quiz.py",
        gate_kind=GateKind.AGENT_KSA,
        probe_id=stage_probe_id(cid, stage_id),
        extra_args=(
            "--class-rel",
            class_rel,
            "--stage",
            stage_id,
        ),
        uses_generic_stage=True,
    )


def _lit(
    stage: str,
    script: str,
    kind: GateKind,
    *,
    probe_id: str = "",
    extra_args: tuple[str, ...] = (),
    reinforce_tail: bool = True,
) -> tuple[str, StageProbeSpec]:
    return stage, StageProbeSpec(
        script=script,
        gate_kind=kind,
        probe_id=probe_id,
        extra_args=extra_args,
        reinforce_tail=reinforce_tail,
    )


LITERACY_STAGE_PROBES: dict[str, StageProbeSpec] = dict(
    [
        ("stage-01-grapheme-cyrl", generic_stage_probe("lessons/literacy-cards", "stage-01-grapheme-cyrl")),
        ("stage-03-words-cyrl", generic_stage_probe("lessons/literacy-cards", "stage-03-words-cyrl")),
        (
            "stage-03b-words-case-apelsin",
            generic_stage_probe("lessons/literacy-cards", "stage-03b-words-case-apelsin"),
        ),
        _lit(
            "stage-04-meta-phonology-vowel-consonant",
            "probe_meta_phonology_quiz.py",
            GateKind.AGENT_KSA,
            probe_id="meta-phonology-quiz",
        ),
        _lit(
            "stage-05-syllable-cyrl",
            "probe_syllable_quiz.py",
            GateKind.AGENT_KSA,
            probe_id="syllable-cyrl-quiz",
        ),
        (
            "stage-06-words-cyrl-corpus",
            StageProbeSpec(
                script="probe_literacy_corpus_quiz.py",
                gate_kind=GateKind.AGENT_KSA,
                probe_id="literacy-corpus-quiz",
                extra_args=("--stage", "stage-06-words-cyrl-corpus", "--limit", "20"),
            ),
        ),
        ("stage-07-meta-language", generic_stage_probe("lessons/literacy-cards", "stage-07-meta-language")),
        ("stage-07b-meta-language-2", generic_stage_probe("lessons/literacy-cards", "stage-07b-meta-language-2")),
        ("stage-07c-register-phrases", generic_stage_probe("lessons/literacy-cards", "stage-07c-register-phrases")),
        _lit(
            "stage-07-closed-class",
            "probe_literacy_closed_class_quiz.py",
            GateKind.AGENT_KSA,
            probe_id="literacy-closed-class-quiz",
        ),
        _lit(
            "stage-08-meta-grammar-person",
            "probe_meta_grammar_person_quiz.py",
            GateKind.SIDECAR_SPEC,
            probe_id="meta-grammar-person",
            reinforce_tail=False,
        ),
        _lit(
            "stage-08b-meta-grammar-case",
            "probe_meta_grammar_case_quiz.py",
            GateKind.SIDECAR_SPEC,
            probe_id="meta-grammar-case",
            reinforce_tail=False,
        ),
        _lit(
            "stage-09-grammar-agreement-pilot",
            "probe_meta_grammar_agreement_quiz.py",
            GateKind.SIDECAR_SPEC,
            probe_id="meta-grammar-agreement",
            reinforce_tail=False,
        ),
        _lit(
            "stage-09b-grammar-possessive",
            "probe_possessive_pilot.py",
            GateKind.SIDECAR_SPEC,
            probe_id="possessive-pilot",
            reinforce_tail=False,
        ),
        ("stage-11-grapheme-latn", generic_stage_probe("lessons/literacy-cards", "stage-11-grapheme-latn")),
    ]
)

VISUAL_STAGE_PROBES: dict[str, StageProbeSpec] = {
    str(st["id"]): generic_stage_probe("lessons/visual-cards", str(st["id"]))
    for st in load_class_manifest("lessons/visual-cards").get("stages") or []
}

VISUAL_STAGE_OVERRIDES: dict[str, StageProbeSpec] = {
    "stage-06-numberline-compare": StageProbeSpec(
        script="probe_nline_compare_quiz.py",
        gate_kind=GateKind.AGENT_KSA,
        probe_id="nline-compare-quiz",
    ),
    "stage-13-sets": StageProbeSpec(
        script="probe_venn_region_quiz.py",
        gate_kind=GateKind.AGENT_KSA,
        probe_id="venn-region-quiz",
    ),
    "stage-15-geom-lex": StageProbeSpec(
        script="probe_geom_lex_quiz.py",
        gate_kind=GateKind.AGENT_KSA,
        probe_id="geom-lex-quiz",
    ),
}
VISUAL_STAGE_PROBES.update(VISUAL_STAGE_OVERRIDES)

LEXICAL_STAGE_PROBES: dict[str, StageProbeSpec] = {
    str(st["id"]): generic_stage_probe("lessons/lexical-cards-ru", str(st["id"]))
    for st in load_class_manifest("lessons/lexical-cards-ru").get("stages") or []
}

MATH_PALOCHKI_PROBE = StageProbeSpec(
    script="probe_math_palochki_bundle.py",
    gate_kind=GateKind.SIDECAR_SPEC,
    probe_id="math-palochki-bundle",
    reinforce_tail=False,
)


def stage_probe_for(class_rel: str, stage_id: str) -> StageProbeSpec | None:
    if class_rel.endswith("literacy-cards"):
        return LITERACY_STAGE_PROBES.get(stage_id)
    if class_rel.endswith("visual-cards"):
        return VISUAL_STAGE_PROBES.get(stage_id)
    if class_rel.endswith("lexical-cards-ru"):
        return LEXICAL_STAGE_PROBES.get(stage_id)
    return None


def all_literacy_stages_have_probe() -> bool:
    manifest = load_class_manifest("lessons/literacy-cards")
    stage_ids = {str(st["id"]) for st in manifest.get("stages") or []}
    return stage_ids <= set(LITERACY_STAGE_PROBES.keys())


def all_visual_stages_have_probe() -> bool:
    manifest = load_class_manifest("lessons/visual-cards")
    stage_ids = {str(st["id"]) for st in manifest.get("stages") or []}
    return stage_ids <= set(VISUAL_STAGE_PROBES.keys())


PHRASE_AGENT_STORE_EVENTS: tuple[str, ...] = (
    "lang.event.transitive.wash.v0",
    "lang.event.transitive.wash.circ.v0",
    "lang.event.ditransitive.give.v0",
    "lang.event.transitive.wash.3sg_fem.v0",
    "lang.event.possessive.pronoun.sg.v0",
    "lang.event.numeral.head.v0",
)

PHRASE_FONT_PT_BY_EVENT: dict[str, int] = {
    "lang.event.transitive.wash.circ.v0": 36,
    "lang.event.ditransitive.give.v0": 40,
}


def resolve_probe_id(spec: StageProbeSpec, report: dict[str, Any] | None = None) -> str:
    if spec.probe_id:
        return spec.probe_id
    rep = report or {}
    return str(rep.get("probe") or "")


def effective_gate_kind(spec: StageProbeSpec, report: dict[str, Any] | None = None) -> GateKind:
    pid = resolve_probe_id(spec, report)
    if pid:
        return gate_kind_for_probe(pid, report)
    return spec.gate_kind


def probe_script_for_stage(class_rel: str, stage_id: str) -> str | None:
    spec = stage_probe_for(class_rel, stage_id)
    return spec.script if spec else None


PROBE_BY_STAGE: dict[str, str] = {
    stage: spec.script for stage, spec in LITERACY_STAGE_PROBES.items()
}

STAGE_PROBE_SPECS: dict[str, StageProbeSpec] = dict(LITERACY_STAGE_PROBES)
