"""Общая инфра teacher probe: store, lock, verdict, отчёт в generated/."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

_CURRICULUM = Path(__file__).resolve().parent
from vc_paths import repo_root  # noqa: E402

_REPO = repo_root(__file__)


def setup_probe_imports() -> Path:
    for entry in (_REPO, _CURRICULUM):
        s = str(entry)
        if s not in sys.path:
            sys.path.insert(0, s)
    from casa._paths import ensure_import_paths

    ensure_import_paths()
    os.chdir(_REPO)
    return _REPO


def default_store(store_id: str = "von-neumann") -> Path:
    return (_REPO / "agents" / store_id).resolve()


def generated_report_path(filename: str) -> Path:
    out = _CURRICULUM / "generated" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def run_spec_regression(
    report: dict[str, Any],
    *,
    report_filename: str,
    print_summary: bool = True,
) -> dict[str, Any]:
    """Sidecar curriculum lint — write report, no mastery credit on agent store."""
    from casa.domain.teacher_gate import annotate_sidecar_report

    out = annotate_sidecar_report(report)
    report_path = generated_report_path(report_filename)
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if print_summary:
        summary = {
            "probe": out.get("probe"),
            "pass": out.get("verdict_pass"),
            "gate_kind": out.get("gate_kind"),
            "path": str(report_path),
        }
        print(json.dumps(summary, ensure_ascii=False))
        print(f"wrote {report_path}")
    return out


def run_phrase_sidecar_probe(
    *,
    probe_id: str,
    rows: list[dict[str, Any]],
    report_filename: str,
    row_pass_key: str = "phrase_know",
) -> dict[str, Any]:
    """Phrase sidecar — synthetic analytic_know reads, rule compose only."""
    ok = bool(rows) and all(bool(r.get(row_pass_key)) for r in rows)
    report = {
        "probe": probe_id,
        "total": len(rows),
        "know": sum(1 for r in rows if r.get(row_pass_key)),
        "pass": ok,
        "rows": rows,
    }
    return run_spec_regression(report, report_filename=report_filename)


def finalize_honest_probe_report(
    state: dict[str, Any],
    report: dict[str, Any],
    *,
    store: Path,
    probe_id: str | None = None,
    tick: int | None = None,
    save_on_pass: bool = True,
) -> dict[str, Any]:
    """Annotate + record mastery for agent KSA probes (store + predict)."""
    from casa.domain.emergent_promote import record_probe_gate
    from casa.domain.mastery_gate import mastery_status
    from casa.domain.teacher_gate import gate_kind_for_probe
    from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

    pid = probe_id or str(report.get("probe") or "")
    kind = gate_kind_for_probe(pid, report)
    out = dict(report)
    out["gate_kind"] = kind.value
    out["credits_mastery"] = kind.value == "agent_ksa"
    t = int(tick if tick is not None else state.get("field_version") or 0)
    gate = record_probe_gate(state, out, tick=t, store_dir=store)
    out["mastery"] = mastery_status(state, pid)
    out["probe_gate"] = {"gate": gate.gate, "passed": gate.passed}
    if gate.skipped:
        out["probe_gate"]["skipped"] = list(gate.skipped)
    if save_on_pass and gate.passed and kind.value == "agent_ksa":
        mark_runtime_dirty(state)
        save_runtime_state(store, state, force=True, sync_ltm_on_save=False)
    return out


def run_lab_experiment_report(
    report: dict[str, Any],
    *,
    report_filename: str,
) -> dict[str, Any]:
    """Lab sweep / experiment — no mastery credit."""
    from casa.domain.teacher_gate import GateKind, annotate_sidecar_report

    out = annotate_sidecar_report(report)
    out["gate_kind"] = GateKind.SIDECAR_SPEC.value
    out["credits_mastery"] = False
    path = generated_report_path(report_filename)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": out.get("probe"), "path": str(path)}, ensure_ascii=False))
    return out


def manifest_hints(class_rel: str = "lessons/literacy-cards") -> dict[str, str]:
    manifest = json.loads((_REPO / class_rel / "class.manifest.json").read_text(encoding="utf-8"))
    return {str(f["id"]): str(f.get("concept_id") or "") for f in manifest.get("frames") or []}


def manifest_hints_merged(*class_rels: str) -> dict[str, str]:
    hints: dict[str, str] = {}
    for rel in class_rels:
        hints.update(manifest_hints(rel))
    return hints


def run_frame_probe(
    *,
    probe: str,
    frames: Sequence[str],
    hint_for_frame: Callable[[str], str],
    predict: Callable[[Any, str], list[tuple[str, int]]],
    report_filename: str,
    lock_holder: str,
    preds_field: str = "lex_top",
    store_id: str = "von-neumann",
    extra_out: dict[str, Any] | None = None,
    print_lines: bool = False,
    line_extra: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.bridge_math import vis_frame_concept_id

    from probe_lex_verdict import verdict_lex_probe

    store = default_store(store_id)
    report_path = generated_report_path(report_filename)

    with store_session_lock(store, holder=lock_holder):
        state = resolve_ingest_state(store, None)
        items: list[dict[str, Any]] = []
        counts = {"know": 0, "ambiguous": 0, "wrong": 0, "empty": 0}
        for fid in frames:
            hint = hint_for_frame(fid)
            preds = predict(state, fid)
            v = verdict_lex_probe(preds, hint)
            counts[str(v["verdict"])] = counts.get(str(v["verdict"]), 0) + 1
            row: dict[str, Any] = {
                "frame_id": fid,
                "vis_concept": vis_frame_concept_id(fid),
                "teacher_hint": hint or None,
                "teacher_guess": v["teacher_guess"],
                "verdict": v["verdict"],
                "matches_hint": v["matches_hint"],
                "top_score": v["top_score"],
                "leaders": v["leaders"],
                preds_field: [{"concept_id": c, "score": s} for c, s in preds],
            }
            if line_extra is not None:
                extra = line_extra(row)
                if extra:
                    row.update(extra)
            items.append(row)

        out_inner: dict[str, Any] = {
            "store_id": store_id,
            "probe": probe,
            "total": len(frames),
            "know": counts["know"],
            "ambiguous": counts["ambiguous"],
            "wrong": counts["wrong"],
            "empty": counts["empty"],
            "matched": counts["know"],
            "items": items,
        }
        if extra_out:
            out_inner.update(extra_out)

        out_inner = finalize_honest_probe_report(
            state,
            out_inner,
            store=store,
            probe_id=probe,
        )

    out = out_inner
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "know": counts["know"],
        "ambiguous": counts["ambiguous"],
        "wrong": counts["wrong"],
        "total": len(frames),
        "path": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if print_lines:
        marks = {"know": "OK", "ambiguous": "??", "wrong": "--", "empty": "  "}
        for it in items:
            mark = marks.get(str(it["verdict"]), "?")
            print(
                f"{mark} {it['frame_id']}: {it['teacher_guess']} "
                f"(hint {it['teacher_hint']}, score {it['top_score']}, verdict {it['verdict']})"
            )
    return out
