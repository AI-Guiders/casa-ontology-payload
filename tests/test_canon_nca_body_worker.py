#!/usr/bin/env python3
"""Canon NCA body extension + standalone worker (no tick/sleep drain)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.body.catalog_canon_nca import canon_nca_function_spec, merge_canon_nca_into_manifest
from casa.body.contracts import FunctionCallIntent
from casa.body.extension import BodyFunctionExtension
from casa.prisms.memory.bootstrap_morph_role_ru import bootstrap_morph_role_lattice
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_body_extension_runs_canon_nca_queue():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-body-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        manifest = merge_canon_nca_into_manifest(
            {
                "schema_version": 1,
                "body_profile_id": "test",
                "default_backend": "in_process",
                "backends": {"in_process": {}},
                "functions": [canon_nca_function_spec()],
            }
        )
        ext = BodyFunctionExtension(tmp, manifest=manifest)
        intent = FunctionCallIntent(
            function_id="tool.memory.run_canon_nca",
            arguments={"max_jobs": 1, "device": "cpu"},
            call_id="test-1",
            provenance={"source": "pytest"},
        )
        result = ext.dispatch(intent)
        assert result.ok
        assert result.structured is not None
        assert result.structured.get("ran", 0) >= 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_worker_cli_status_only():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-worker-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        script = REPO_ROOT / "tools" / "run_canon_nca_worker.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--store-dir", str(tmp), "--status-only"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)
        assert "morph-role-ru" in data.get("canon_targets", [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
