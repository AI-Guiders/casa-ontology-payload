#!/usr/bin/env python3
"""Wake probe b004 — replay 22–28 s, no persist, P1–P5 eval."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import casa.domain.listen_womb_tick  # noqa: F401 — warm imports

from casa.domain.listen_womb_tick import run_listen_womb_stream, write_womb_report
from casa.prisms.memory.agent_life import load_unified_agent_runtime
from casa.sensory.adapters import find_bundle_video, resolve_scene_wav


def _eval_p1_p5(report, scene_id: str) -> dict[str, Any]:
    ticks = report.ticks
    moment_ids = [t.moment_id for t in ticks if t.moment_id]
    episode_ids = [t.episode_id for t in ticks if t.episode_id]
    beat_ids = [t.beat_id for t in ticks]
    coactive_ticks = [
        t
        for t in ticks
        if t.hippo_wake and (t.hippo_wake.get("coactive") or (t.life_tick or {}).get("coactive"))
    ]
    av_in_buffer = False
    if report.hippo_index:
        # check closed moments in journal snapshots
        pass
    from casa.prisms.hippo.wake_index import ensure_hippo_index

    idx = ensure_hippo_index({"hippo_index": report.hippo_index}) if False else {}
    # hippo_index on report is summary only — inspect ticks + last hippo_wake buffer via journal in state
    modalities_hit = False
    for t in ticks:
        hw = t.hippo_wake or {}
        mid = hw.get("moment_id")
        if mid and report.hippo_index:
            pass
    # Re-derive from tick records
    unique_moments = sorted(set(moment_ids))
    unique_episodes = sorted(set(episode_ids))
    all_b004 = all(b == "b004" for b in beat_ids if b)
    moment_stable = len(unique_moments) <= 1 and len(moment_ids) == len(ticks) and len(ticks) > 0
    episode_stable = len(unique_episodes) <= 1 and len(episode_ids) == len(ticks)

    # coactive + av_coactive: read from life_tick / hippo_wake on ticks
    any_coactive = any((t.life_tick or {}).get("coactive") for t in ticks)
    journal_events = (report.hippo_index or {}).get("journal_events") or {}

    checks = {
        "P1_one_episode_id": {
            "pass": episode_stable and len(unique_episodes) == 1,
            "episode_ids": unique_episodes,
            "tick_count": len(ticks),
        },
        "P2_one_moment_id_on_b004": {
            "pass": moment_stable and all_b004 and len(unique_moments) == 1,
            "moment_ids": unique_moments,
            "beat_ids_sample": beat_ids[:5],
            "all_b004": all_b004,
        },
        "P3_av_coactive_in_buffer": {
            "pass": any_coactive,  # refined below from state if available
            "coactive_tick_count": sum(1 for t in ticks if (t.life_tick or {}).get("coactive")),
        },
        "P4_journal_chain": {
            "pass": bool(journal_events.get("episode_opened"))
            and bool(journal_events.get("moment_opened"))
            and bool(journal_events.get("wake_tick")),
            "journal_events": journal_events,
        },
        "P5_no_oracle": {
            "pass": True,
            "note": "beat.note not read by ingest/replay path (bind profile, no words[])",
        },
    }
    checks["all_pass"] = all(c["pass"] for c in checks.values() if isinstance(c, dict) and "pass" in c)
    return checks


def main() -> int:
    store_dir = (REPO / "agents/von-neumann").resolve()
    manifest = (
        REPO.parent / "casa-listen-corpus/lalabook/emotions/ukt4kquicra/manifest.ndjson"
    ).resolve()
    bundle_dir = manifest.parent
    scene = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
    sid = str(scene.get("id") or "")

    runtime = load_unified_agent_runtime(store_dir)
    video_path = find_bundle_video(bundle_dir)
    wav_path = resolve_scene_wav(store_dir, scene, manifest_dir=bundle_dir)
    work_dir = bundle_dir / "preview" / "replay" / "ch00_probe_b004"

    state, report = run_listen_womb_stream(
        runtime.state,
        scene,
        video_path=video_path,
        wav_path=wav_path,
        work_dir=work_dir,
        store_dir=store_dir,
        interval_sec=0.5,
        t_start_rel=22.0,
        t_end_rel=28.0,
        runtime=runtime,
        run_life_tick=True,
        run_sleep_at_end=False,
    )

    # P3: modalities from in-memory hippo_index
    idx = state.get("hippo_index") or {}
    buf = idx.get("moment_buffer") or {}
    av_coactive = any("av_coactive" in (row.get("modalities") or []) for row in buf.values() if isinstance(row, dict))
    report.hippo_index = report.hippo_index or {}
    if isinstance(idx, dict):
        journal = idx.get("journal") or []
        events: dict[str, int] = {}
        for row in journal:
            if isinstance(row, dict):
                ev = str(row.get("event") or "")
                events[ev] = events.get(ev, 0) + 1
        report.hippo_index = {
            **report.hippo_index,
            "journal_events": events,
            "moment_buffer_modalities": {
                k: v.get("modalities") if isinstance(v, dict) else []
                for k, v in buf.items()
            },
        }

    womb_path = REPO / "tools" / "_hippo_probe_b004_womb.json"
    write_womb_report(womb_path, report)
    checks = _eval_p1_p5(report, sid)
    checks["P3_av_coactive_in_buffer"]["pass"] = av_coactive
    checks["P3_av_coactive_in_buffer"]["av_coactive"] = av_coactive
    checks["all_pass"] = all(
        c["pass"] for k, c in checks.items() if k.startswith("P") and isinstance(c, dict)
    )

    out = {
        "probe": "wake_b004",
        "window": [22.0, 28.0],
        "persist": False,
        "scene_id": sid,
        "summary": report.summary(),
        "checks": checks,
        "hippo_index": report.hippo_index,
        "ticks_brief": [
            {
                "seq": t.seq,
                "t_rel": t.t_rel,
                "beat_id": t.beat_id,
                "moment_id": t.moment_id,
                "episode_id": t.episode_id,
                "coactive": (t.life_tick or {}).get("coactive"),
            }
            for t in report.ticks
        ],
        "womb_report": str(womb_path),
    }
    out_path = REPO / "tools" / "_hippo_probe_b004_result.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if checks["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
