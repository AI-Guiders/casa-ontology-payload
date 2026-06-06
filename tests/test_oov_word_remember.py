#!/usr/bin/env python3
"""ADR-0049 L2 OOV smoke — remember → recall → bind."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from casa.prisms.memory.agent_memory_ops import agent_recall, agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_oov_remember_recall_smoke():
    tmp = Path(tempfile.mkdtemp(prefix="casa-oov-test-"))
    try:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        rep = agent_remember(
            tmp,
            state,
            {
                "kind": "hypothesis",
                "text": "«криббл» — вымышленное слово.",
                "concepts": ["lang.word.криббл"],
                "tags": ["oov-smoke"],
                "status": "confirmed",
                "test_cues": ["криббл"],
            },
        )
        assert rep.get("remembered")
        recall = agent_recall(tmp, query="криббл", limit=5)
        texts = " ".join(str(r.get("text") or "") for r in recall.get("records") or [])
        assert "криббл" in texts.lower()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
