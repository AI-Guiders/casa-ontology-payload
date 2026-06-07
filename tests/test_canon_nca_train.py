#!/usr/bin/env python3
"""Canon lattice NCA queue — promote/bootstrap → pending → body train → agent commit."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from casa.body.completion_percept import body_completions_path
from casa.prisms.memory.agent_canon_lattice import agent_promote_canon_lattice
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.bootstrap_morph_role_ru import bootstrap_morph_role_lattice
from casa.prisms.memory.canon_nca_train import (
    agent_commit_canon_nca_completion,
    enqueue_canon_nca_train,
    list_canon_nca_status,
    read_train_complete,
    run_pending_canon_nca_trains,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.nca_registry import load_registry


def test_promote_enqueues_canon_nca():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-promote-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        src = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "De Morgan",
                "concepts": ["math.logic.de_morgan"],
                "tags": ["logic-lab"],
                "status": "confirmed",
            },
        )
        rep = agent_promote_canon_lattice(
            tmp,
            state,
            {
                "lattice_id": "logic-laws",
                "concept_ids": ["math.logic.de_morgan"],
                "source_journal_id": src.get("journal_id"),
                "reason": "smoke",
            },
            allow_unconfirmed=True,
        )
        assert rep.get("nca_train", {}).get("enqueued")
        reg = load_registry(tmp)
        assert "logic-laws" in (reg.get("pending") or [])
        reqs = reg.get("pending_requests") or []
        assert any(r.get("lattice_id") == "logic-laws" and r.get("actor") == "agent" for r in reqs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bootstrap_morph_enqueues_host_nca():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-morph-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        rep = bootstrap_morph_role_lattice(tmp, state, persist=False)
        assert rep.get("nca_train", {}).get("enqueued")
        reg = load_registry(tmp)
        assert "morph-role-ru" in (reg.get("pending") or [])
        assert any(r.get("actor") == "host" for r in reg.get("pending_requests") or [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_pending_skips_without_train_tool():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-run-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        run = run_pending_canon_nca_trains(tmp, state, max_jobs=1, allow_missing_tool=True)
        assert run.get("ran", 0) >= 1
        assert any(
            r.get("skipped") and r.get("reason") == "train_tool_missing" for r in run.get("results") or []
        )
        reg = load_registry(tmp)
        assert "morph-role-ru" in (reg.get("pending") or [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_body_train_leaves_pending_until_agent_commit():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-await-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        nca_dir = tmp / "nca" / "morph-role-ru"
        nca_dir.mkdir(parents=True, exist_ok=True)
        (nca_dir / "model.pt").write_bytes(b"fake-model")
        from casa.prisms.memory.canon_nca_train import write_train_complete

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
        reg_before = load_registry(tmp)
        assert "morph-role-ru" in (reg_before.get("pending") or [])
        rep = agent_commit_canon_nca_completion(tmp, state, "morph-role-ru", persist=False)
        assert rep.get("committed")
        reg_after = load_registry(tmp)
        assert "morph-role-ru" not in (reg_after.get("pending") or [])
        assert read_train_complete(tmp, "morph-role-ru") is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_enqueue_rejects_non_canon_lattice():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-reject-"))
    try:
        import pytest

        with pytest.raises(ValueError, match="not a canon NCA"):
            enqueue_canon_nca_train(tmp, "lexicon-ru-foo-bar", reason="bad", actor="agent")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_canon_nca_status_includes_morph():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-list-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        bootstrap_morph_role_lattice(tmp, state, persist=False)
        st = list_canon_nca_status(state, tmp)
        assert "morph-role-ru" in st.get("canon_targets", [])
        row = next(r for r in st.get("rows") or [] if r.get("lattice_id") == "morph-role-ru")
        assert row.get("token_count", 0) >= 4
        assert row.get("pending") is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_completion_percept_path_exists_after_emit():
    tmp = Path(tempfile.mkdtemp(prefix="casa-nca-percept-"))
    try:
        from casa.prisms.memory.canon_nca_train import emit_canon_nca_completion_percept

        emit_canon_nca_completion_percept(
            tmp,
            {"lattice_id": "morph-role-ru", "trained": True, "awaiting_agent_commit": True},
        )
        assert body_completions_path(tmp).is_file()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
