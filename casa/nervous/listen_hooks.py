"""Listen-only afferent hooks for impulse trace (developmental stage 0)."""

from __future__ import annotations

from typing import Any

from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import impulse_recorder


def record_listen_imprint_impulse(
    *,
    store_dir,
    scene_id: str,
    caption: str,
    words_expected: list[str],
    heard: list[dict[str, Any]],
    recalled: list[dict[str, Any]],
    field_version_before: int,
    field_version_after: int,
    auditory: dict[str, Any] | None = None,
    auditory_tokens: list[str] | None = None,
    visual: dict[str, Any] | None = None,
    visual_tokens: list[str] | None = None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    zones = ["linguistic"]
    with rec.channel(ImpulseChannel.LISTEN_IMPRINT, store_dir=store_dir) as imp:
        imp.select(
            "field_delta",
            zone="linguistic",
            selected=["imprinted"],
            inputs={
                "scene_id": scene_id,
                "caption": caption,
                "field_version_before": field_version_before,
                "field_version_after": field_version_after,
                "words_expected": words_expected,
                "words_heard": len(heard),
            },
        )
        potentials = [
            {
                "id": str(row.get("word") or ""),
                "score": int(row.get("score") or 0),
                "reason": "scene_link",
            }
            for row in recalled[:12]
            if isinstance(row, dict)
        ]
        imp.select(
            "listen_imprint",
            zone="linguistic",
            selected=[str(row.get("word") or "") for row in recalled if isinstance(row, dict)],
            potentials=potentials,
            inputs={
                "scene_id": scene_id,
                "recall_count": len(recalled),
            },
        )
        if auditory:
            zones.append("auditory")
            dyn = [t for t in (auditory_tokens or []) if t.startswith("A:dyn:")]
            binaural = [t for t in (auditory_tokens or []) if t.startswith("A:itd:") or t.startswith("A:ild:")]
            imp.select(
                "auditory_imprint",
                zone="auditory",
                selected=dyn or ["imprinted"],
                inputs={
                    "scene_id": scene_id,
                    "codec_id": auditory.get("codec_id"),
                    "duration_ms": auditory.get("duration_ms"),
                    "placements": auditory.get("placements"),
                    "speaker": auditory.get("speaker"),
                },
            )
            if binaural:
                imp.select(
                    "binaural_cues",
                    zone="auditory",
                    selected=binaural[:8],
                    inputs={"itd_ild_tokens": len(binaural)},
                )
        if visual:
            zones.append("visual")
            scene_tok = f"V:scene:{scene_id}"
            imp.select(
                "visual_imprint",
                zone="visual",
                selected=[scene_tok] if scene_tok in (visual_tokens or []) else ["imprinted"],
                inputs={
                    "scene_id": scene_id,
                    "codec_id": visual.get("codec_id"),
                    "placements": visual.get("placements"),
                    "frame_id": visual.get("frame_id"),
                },
            )
        summary = imp.finish(ImpulseOutcome.SILENT, zones_touched=zones)
        return dict(summary)
    return None
