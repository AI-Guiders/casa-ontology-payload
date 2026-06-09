"""Working Memory Prism — policy resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_prism import ensure_agent_prism

from .model import DEFAULT_WM_POLICY


def _apply_genetic_wm_policy(state: dict, policy: dict[str, Any]) -> None:
    try:
        from casa.prisms.genetic import genetic_constant

        for path, key in (
            ("signal_decay.wm_theta_decay", "theta_decay"),
            ("signal_decay.wm_theta_decay_floor", "theta_decay"),
        ):
            val = genetic_constant(state, path)
            if val is not None:
                policy[key] = float(val)
                break
    except (ImportError, AttributeError, TypeError, ValueError):
        pass


def get_wm_policy(state: dict, store_dir: Path | None = None) -> dict[str, Any]:
    policy = json.loads(json.dumps(DEFAULT_WM_POLICY))
    _apply_genetic_wm_policy(state, policy)
    block = ensure_agent_prism(state)
    override = block.get("wm_policy")
    if isinstance(override, dict):
        policy.update({k: v for k, v in override.items() if k != "score_weights"})
        sw = override.get("score_weights")
        if isinstance(sw, dict):
            policy["score_weights"] = {**policy["score_weights"], **sw}
    if store_dir is not None:
        from casa.prisms.shared.store_layout import agent_manifest_path

        path = agent_manifest_path(store_dir)
        if path.is_file():
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
            mp = manifest.get("wm_policy")
            if isinstance(mp, dict):
                policy.update({k: v for k, v in mp.items() if k != "score_weights"})
                sw = mp.get("score_weights")
                if isinstance(sw, dict):
                    policy["score_weights"] = {**policy["score_weights"], **sw}
    return policy
