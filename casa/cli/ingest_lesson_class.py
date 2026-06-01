#!/usr/bin/env python3
"""Ingest a lesson class (manifest + math bundle) into living agent store."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_stack import rank_cue_on_f0, decode_f0_lattice
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def ingest_lesson_class(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
    sleep_after_each_lesson: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest_path = class_dir / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_path = class_dir / str(manifest.get("bundle") or "kb-math-palochki-v1.bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["last_class"] = manifest.get("class_id")

    math_rep = ingest_math_bundle(state, bundle, lattice_id=SCHEMA_MATH)
    lesson_reports: list[dict[str, Any]] = []
    episodes_total = 0

    for lesson in manifest.get("lessons") or []:
        ep_ids: list[str] = []
        for raw in lesson.get("episodes") or []:
            ep = append_episode(
                state,
                cue=str(raw.get("cue") or ""),
                surface_attempt=str(raw.get("surface_attempt") or ""),
                correct=str(raw.get("correct") or ""),
                lattice_id=str(raw.get("lattice_id") or SCHEMA_MATH),
                concept_id=str(raw.get("concept_id") or "") or None,
                scene=str(raw.get("scene") or ""),
                bundle=bundle,
                structure_tag=raw.get("structure_tag"),
                episode_source="ingest",
            )
            if ep:
                ep_ids.append(str(ep.get("id") or ""))
                episodes_total += 1
        sleep_rep = None
        if sleep_after_each_lesson and ep_ids:
            sleep_rep = run_sleep(state, bundle)
        lesson_reports.append(
            {
                "id": lesson.get("id"),
                "title": lesson.get("title"),
                "episodes": len(ep_ids),
                "sleep": sleep_rep,
            }
        )

    probes: list[dict[str, Any]] = []
    lattices = memory_lattices(state)
    lat = lattices.get(SCHEMA_MATH) or {}
    if lat.get("cells"):
        dec = decode_f0_lattice(lat)
        for row in manifest.get("probe") or []:
            cue = str(row.get("cue") or "")
            expect = str(row.get("expect") or "")
            ranked = rank_cue_on_f0(dec, cue)
            top = ranked[0][0] if ranked else None
            probes.append({"cue": cue, "expect": expect, "top": top, "pass": top == expect})

    report: dict[str, Any] = {
        "store_dir": str(store_dir),
        "class_id": manifest.get("class_id"),
        "class_dir": str(class_dir),
        "math_ingest": math_rep,
        "lessons": lesson_reports,
        "episodes_total": episodes_total,
        "probe": probes,
        "field_version": state.get("field_version"),
    }

    if persist:
        mark_runtime_dirty(state)
        report["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=True,
        )
        (store_dir / "bundles").mkdir(exist_ok=True)
        dest = store_dir / "bundles" / bundle_path.name
        dest.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (class_dir / "last-ingest-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest lesson class into agent store")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/math-palochki")
    p.add_argument("--no-persist", action="store_true")
    p.add_argument("--no-sleep", action="store_true")
    args = p.parse_args()

    rep = ingest_lesson_class(
        args.store_dir or default_agent_store(),
        args.class_dir,
        sleep_after_each_lesson=not args.no_sleep,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
