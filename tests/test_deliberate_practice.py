#!/usr/bin/env python3
from __future__ import annotations

from casa.domain.deliberate_practice import (
    apply_deliberate_practice,
    weakest_link_from_probe_report,
    weakest_link_from_surprise,
)
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions


def test_weakest_link_from_phrase_report():
    report = {
        "word_reads": [
            {
                "surface": "мыла",
                "slug": "x",
                "chain": {
                    "segments": [
                        {"syllable": "мы", "verdict": "know", "top_score": 4, "leaders": ["syllable.мы"]},
                        {"syllable": "ла", "verdict": "ambiguous", "top_score": 4, "leaders": ["syllable.ла", "syllable.мы"], "frame_id": "syllable-ла-sans", "teacher_hint": "syllable.ла"},
                    ]
                },
            }
        ]
    }
    weak = weakest_link_from_probe_report(report)
    assert weak is not None
    assert weak["concept_id"] == "syllable.ла"


def test_apply_deliberate_practice_to_wm():
    wm = WorkingMemory()
    link = weakest_link_from_surprise(
        ControlExtensions(
            predicted=(),
            surprise=("syllable.ла",),
            prediction_error=0.5,
            dan_mask=(),
            sparse_ratio=0.0,
            masked_digest=(),
            value=0.5,
        )
    )
    rep = apply_deliberate_practice(wm, link)
    assert rep is not None
    assert wm.step_focus == "syllable-ла-sans"
    assert wm.goal_id.startswith("goal.practice.")
