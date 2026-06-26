#!/usr/bin/env python3
"""Listen scene compositor (CCU) — capture → imprint on field (ADR-0027 § CCU + ADR-0028).

Layer map:
  adapters.listen_corpus  → resolved paths (file_replay)
  codecs (retinal/cochlear) → inside imprint_* in prisms
  listen_moment           → one multimodal moment on scene_id
  listen_womb_tick        → wall-clock stream steps + life tick
"""

from __future__ import annotations

from casa.prisms.memory.listen_moment import listen_moment

__all__ = ["listen_moment"]
