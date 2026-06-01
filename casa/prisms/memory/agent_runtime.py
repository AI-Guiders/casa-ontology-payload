#!/usr/bin/env python3
"""Host bridge only — boot OS process; life is in `agent_life.py`."""

from __future__ import annotations

from casa.prisms.memory.agent_life import (
    agent_live_loop,
    agent_life_tick,
    agent_wake,
    default_agent_wake,
    load_agent_session,
    resolve_agent_bundle,
    save_agent_session,
)


def agent_run(store_dir, **kwargs):  # type: ignore[no-untyped-def]
    """Legacy alias."""
    stop = kwargs.pop("max_ticks", kwargs.pop("stop_after", None))
    for key in ("notebook", "bundle_name", "bundle", "display_name"):
        kwargs.pop(key, None)
    return agent_wake(store_dir, stop_after=stop, **kwargs)


default_agent_run = default_agent_wake
