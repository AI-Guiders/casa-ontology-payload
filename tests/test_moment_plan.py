"""Teacher moment plan from manifest (lab authoring)."""

from __future__ import annotations

from pathlib import Path

from casa.cli.moment_plan import build_moment_steps, load_manifest, stage_ids_in_order


def test_stage_order() -> None:
    manifest = load_manifest(Path("lessons/visual-cards"))
    ids = stage_ids_in_order(manifest)
    assert ids[0] == "stage-01-count"
    assert ids[-1] == "stage-15-geom-lex"
    assert len(ids) == 15


def test_stage_07_has_paired_math() -> None:
    manifest = load_manifest(Path("lessons/visual-cards"))
    steps = build_moment_steps(manifest, "stage-07-numberline-add")
    kinds = [("math" if "math" in s else "visual") for s in steps]
    assert kinds.count("visual") == 2
    assert kinds.count("math") >= 2
    assert any(s.get("math", {}).get("concept_id") == "math.op.add" for s in steps)
