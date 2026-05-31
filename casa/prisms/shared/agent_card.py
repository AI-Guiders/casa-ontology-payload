#!/usr/bin/env python3
"""Load agent-card v0 manifest."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path


def read_agent_card(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_checkpoint(card: dict, bundle_name: str, tiers: dict) -> Path:
    """Pick model_phase1 (easy) or model_hard (hard) for a bundle."""
    tier_row = next((r for r in tiers.get("bundles", []) if r["bundle"] == bundle_name), None)
    tier = tier_row["tier"] if tier_row else "easy"
    ckpt = card.get("checkpoints") or {}
    if tier == "hard" and ckpt.get("model_hard"):
        return Path(ckpt["model_hard"])
    if ckpt.get("model_phase1"):
        return Path(ckpt["model_phase1"])
    return Path(ckpt["model"])
