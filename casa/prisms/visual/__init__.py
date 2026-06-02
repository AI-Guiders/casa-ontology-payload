"""Visual content prism — LRGB imprint + vis.* anchors (ADR-0028 / ADR-0018)."""

from casa.prisms.visual.bootstrap import (
    VIS_CONCEPT_PREFIX,
    VIS_OBJECT,
    ensure_prism_visual,
)
from casa.prisms.visual.imprint import apply_visual_imprint, imprint_visual_frame
from casa.prisms.visual.ingest_room import ingest_room_frames
from casa.prisms.visual.ingest_vis import ingest_vis_batch, ingest_vis_claim
from casa.prisms.visual.predict_vis import predict_vis

__all__ = [
    "VIS_OBJECT",
    "VIS_CONCEPT_PREFIX",
    "ensure_prism_visual",
    "apply_visual_imprint",
    "imprint_visual_frame",
    "ingest_room_frames",
    "ingest_vis_claim",
    "ingest_vis_batch",
    "predict_vis",
]
