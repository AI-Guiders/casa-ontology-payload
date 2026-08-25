#!/usr/bin/env python3
"""One-off: summarize myhodron ch1 replay + impulse trace."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.prisms.auditory.imprint import auditory_tokens_on_field
from casa.prisms.memory.agent_life import load_unified_agent_runtime
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.visual.imprint import visual_tokens_on_field


def main() -> int:
    out_path = Path("tools/_myhodron_replay_out.json")
    text = out_path.read_text(encoding="utf-8-sig")
    start = text.find("{")
    data = json.loads(text[start:])

    print("=== REPLAY SUMMARY ===")
    print("replayed:", data.get("replayed"))
    print("field_version:", data.get("field_version"))
    for r in data.get("reports") or []:
        s = r.get("summary") or {}
        print(
            f"ch{r.get('chapter')} ticks={s.get('life_tick_count')} "
            f"surprise={s.get('life_surprise_ticks')} "
            f"imprint={s.get('imprint_ticks')} "
            f"coactive={s.get('percept_av_coactive_ticks')}"
        )

    it = data.get("impulse_trace") or {}
    print("trace rows total read:", it.get("rows"))
    print("channels:", it.get("channels"))

    store = Path("agents/von-neumann")
    trace_path = store / "nervous" / "impulse_trace.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent = rows[-800:]

    by_ch = Counter(r.get("channel") for r in recent)
    print("\n=== LAST 800 TRACE ROWS BY CHANNEL ===")
    for ch, n in by_ch.most_common():
        print(f"  {ch}: {n}")

    aff = [r for r in recent if r.get("channel") == "affect_listen"]
    drv_counts: Counter[str] = Counter()
    theme_hits = 0
    for r in aff:
        for ev in r.get("events") or []:
            if ev.get("kind") != "activate":
                continue
            inp = ev.get("inputs") or {}
            for d in inp.get("drivers") or []:
                drv_counts[str(d)] += 1
            if inp.get("theme_cluster"):
                theme_hits += 1
    print(f"\n=== AFFECT_LISTEN ({len(aff)} rows) ===")
    print("driver hits:", dict(drv_counts))
    print("rows with theme_cluster:", theme_hits)

    av = [r for r in recent if r.get("channel") == "av_coactive"]
    bound = sum(
        1
        for r in av
        for e in r.get("events") or []
        if e.get("kind") == "select" and (e.get("inputs") or {}).get("bound")
    )
    print(f"\n=== AV_COACTIVE ({len(av)} rows, bound={bound}) ===")

    pl = [r for r in recent if r.get("channel") == "percept_life"]
    coactive_ticks = sum(
        1
        for r in pl
        for e in r.get("events") or []
        if (e.get("inputs") or {}).get("coactive")
    )
    print(f"=== PERCEPT_LIFE ({len(pl)} rows, coactive={coactive_ticks}) ===")

    for r in reversed(aff):
        evs = r.get("events") or []
        if evs:
            print("\nSample affect_listen:", json.dumps(evs[0], ensure_ascii=False)[:600])
            break

    rt = load_unified_agent_runtime(store)
    st = ensure_prisms(rt.state)
    lat = memory_lattices(st)
    print("\n=== PRISM LATTICES (memory, selected) ===")
    for name in sorted(lat.keys()):
        if name.startswith("L") or "aud" in name.lower() or "vis" in name.lower():
            cells = lat[name].get("cells") or {}
            print(f"  {name}: cells={len(cells)}")

    manifest = Path(
        r"d:/Experiments/PersonalCursorFolder/Financial/software/open/"
        r"casa-listen-corpus/lalabook/emotions/ukt4kquicra/manifest.ndjson"
    )
    sid = ""
    title = ""
    for line in manifest.read_text(encoding="utf-8").splitlines():
        sc = json.loads(line)
        if sc.get("chapter_index") == 1:
            sid = str(sc["id"])
            title = str(sc.get("chapter_title") or "")
            break
    print(f"\nscene: {sid[:70]}...")
    print(f"title: {title[:90]}")
    a = auditory_tokens_on_field(st, sid)
    v = visual_tokens_on_field(st, sid)
    print(f"A tokens on field: {len(a)}, V tokens: {len(v)}")
    print("A sample:", a[:4])
    print("V sample:", v[:4])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
