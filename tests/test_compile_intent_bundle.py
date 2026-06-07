#!/usr/bin/env python3
"""compile_intent_bundle — pending ru.tract.* → KB bundle."""

from __future__ import annotations

import json
from pathlib import Path

from tools.compile_intent_bundle import compile_pending_claims


def test_compile_pending_tract_claims(tmp_path: Path) -> None:
    bundle_path = tmp_path / "tract.bundle.json"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "pending_tract_claims": [
                    {
                        "concept_id": "ru.tract.lab-note",
                        "slots": {
                            "cue_words": "лаборатория,гипотеза",
                            "requires_geometry": "dialogue_turn",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pending = json.loads(manifest_path.read_text(encoding="utf-8"))["pending_tract_claims"]
    rep = compile_pending_claims(pending, bundle_path, clear_manifest_pending=manifest_path)
    assert rep["merged"] == 1
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    by_id = {c["concept_id"]: c for c in bundle["claims"]}
    assert "ru.tract.lab-note" in by_id
    assert "гипотеза" in by_id["ru.tract.lab-note"]["slots"]["cue_words"]
    cleared = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert cleared["pending_tract_claims"] == []
