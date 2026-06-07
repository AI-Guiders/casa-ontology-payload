#!/usr/bin/env python3
"""Macro tick ingest of body/completions.jsonl → episode + agent commit."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa.body.completion_ingest import ingest_body_completions_on_tick
from casa.body.completion_percept import append_body_completion_percept, body_completions_path
from casa.prisms.memory.agent_life import agent_life_tick
from casa.prisms.memory.bootstrap_morph_role_ru import bootstrap_morph_role_lattice
from casa.prisms.memory.canon_nca_train import CANON_NCA_FUNCTION_ID, write_train_complete
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.nca_registry import load_registry


def test_ingest_commits_canon_nca_on_tick():
    tmp = Path(tempfile.mkdtemp(prefix="casa-body-ingest-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        session: dict = {"macro_ticks": 0, "self_drive": {}}
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        nca_dir = tmp / "nca" / "morph-role-ru"
        nca_dir.mkdir(parents=True, exist_ok=True)
        (nca_dir / "model.pt").write_bytes(b"fake-model")
        write_train_complete(
            tmp,
            {
                "lattice_id": "morph-role-ru",
                "model_path": "nca/morph-role-ru/model.pt",
                "repair_ratio": 0.5,
                "token_count": 5,
                "train_fingerprint": "abc",
            },
        )
        append_body_completion_percept(
            tmp,
            function_id=CANON_NCA_FUNCTION_ID,
            ok=True,
            summary="canon NCA train complete: morph-role-ru",
            structured={
                "lattice_id": "morph-role-ru",
                "trained": True,
                "awaiting_agent_commit": True,
                "model_path": "nca/morph-role-ru/model.pt",
            },
            provenance={"lattice_id": "morph-role-ru"},
        )
        rep = ingest_body_completions_on_tick(tmp, state, session)
        assert rep.get("ingested") == 1
        assert rep.get("committed") == 1
        reg = load_registry(tmp)
        assert "morph-role-ru" not in (reg.get("pending") or [])
        assert session.get("body", {}).get("completions_line_offset") == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_agent_life_tick_drains_completions_once():
    tmp = Path(tempfile.mkdtemp(prefix="casa-life-ingest-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        session: dict = {"macro_ticks": 0, "self_drive": {"kolb_runs": 0}, "hippo_sleep_threshold": 8}
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        nca_dir = tmp / "nca" / "morph-role-ru"
        nca_dir.mkdir(parents=True, exist_ok=True)
        (nca_dir / "model.pt").write_bytes(b"fake-model")
        write_train_complete(
            tmp,
            {
                "lattice_id": "morph-role-ru",
                "model_path": "nca/morph-role-ru/model.pt",
                "repair_ratio": 0.5,
                "token_count": 5,
                "train_fingerprint": "abc",
            },
        )
        append_body_completion_percept(
            tmp,
            function_id=CANON_NCA_FUNCTION_ID,
            ok=True,
            summary="canon NCA train complete: morph-role-ru",
            structured={"lattice_id": "morph-role-ru", "trained": True},
        )
        tick1 = agent_life_tick(tmp, state, session, bundle=None)
        assert tick1.get("body_completions", {}).get("committed") == 1
        reg = load_registry(tmp)
        assert "morph-role-ru" not in (reg.get("pending") or [])
        lines_before = len(body_completions_path(tmp).read_text(encoding="utf-8").splitlines())
        tick2 = agent_life_tick(tmp, state, session, bundle=None)
        assert "body_completions" not in tick2 or tick2.get("body_completions", {}).get("ingested") == 0
        assert len(body_completions_path(tmp).read_text(encoding="utf-8").splitlines()) == lines_before
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
