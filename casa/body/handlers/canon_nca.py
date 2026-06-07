#!/usr/bin/env python3
"""Body extension handler — drain canon NCA queue (parallel to agent tick/sleep)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from casa.body.contracts import FunctionCallResult, FunctionSpec
from casa.body.handlers.registry import register_handler

FUNCTION_ID = "tool.memory.run_canon_nca"


def _load_state(store_dir: Path) -> dict[str, Any]:
    from casa.prisms.memory.memory_prisms import ensure_prisms
    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.shared.store_layout import field_state_path

    fs = field_state_path(store_dir)
    if fs.is_file():
        return ensure_prisms(load_field_state(fs))
    return ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})


def execute_run_canon_nca(
    spec: FunctionSpec,
    arguments: dict[str, Any],
    store_dir: Path | None,
) -> FunctionCallResult:
    t0 = time.perf_counter()
    if store_dir is None:
        return FunctionCallResult(
            call_id="",
            function_id=spec.function_id,
            ok=False,
            summary="store_dir is required",
            error_code="store_dir_missing",
            wire_backend="in_process",
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    from casa.prisms.memory.canon_nca_train import run_pending_canon_nca_trains

    max_jobs = max(1, int(arguments.get("max_jobs") or 1))
    device = str(arguments.get("device") or "cpu")
    state = _load_state(store_dir)
    report = run_pending_canon_nca_trains(
        store_dir,
        state,
        max_jobs=max_jobs,
        device=device,
        agent_commit=False,
    )
    ok = report.get("ran", 0) >= 0
    awaiting = sum(1 for r in report.get("results") or [] if r.get("awaiting_agent_commit"))
    return FunctionCallResult(
        call_id="",
        function_id=spec.function_id,
        ok=ok,
        summary=(
            f"canon NCA body: trained={report.get('trained', 0)} "
            f"awaiting_agent_commit={awaiting}"
        ),
        structured={**report, "agent_persist_required": bool(awaiting or report.get("trained"))},
        wire_backend="in_process",
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )


register_handler(FUNCTION_ID, execute_run_canon_nca)
