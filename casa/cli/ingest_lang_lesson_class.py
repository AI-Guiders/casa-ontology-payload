#!/usr/bin/env python3
"""Ingest lang lesson class (listen scenes/words + math role cross-links)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links, rank_cue_on_f0
from casa.prisms.memory.lexicon_shard import concept_votes_l2
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.memory.vocab import listen_scene, listen_word, recall_words_for_scene
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _scene_map(bundle: dict) -> dict[str, dict]:
    return {str(s.get("id") or ""): s for s in (bundle.get("scenes") or [])}


def ingest_lang_lesson_class(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
    lesson_ids: list[str] | None = None,
    sleep_after_each_lesson: bool = True,
    word_copies: int = 4,
    link_copies: int = 5,
    persist: bool = True,
    state: dict | None = None,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest_path = class_dir / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_path = class_dir / str(manifest.get("bundle") or "kb-lang-ru-math-bridge-v1.bundle.json")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    scenes = _scene_map(bundle)

    state = resolve_ingest_state(store_dir, state)
    state["store"]["last_class"] = manifest.get("class_id")

    lattices = memory_lattices(state)
    if not (lattices.get(SCHEMA_MATH) or {}).get("cells"):
        raise RuntimeError(
            f"schema-math missing on {store_dir}; ingest math-palochki first "
            f"(requires_math_class={manifest.get('requires_math_class')!r})"
        )

    lesson_reports: list[dict[str, Any]] = []
    words_heard = 0
    links_minted = 0
    math_episodes = 0
    filter_ids = set(lesson_ids) if lesson_ids else None

    for lesson in manifest.get("lessons") or []:
        if filter_ids is not None and str(lesson.get("id") or "") not in filter_ids:
            continue
        scene_heard: list[dict[str, Any]] = []
        lesson_math_eps = 0
        for sid in lesson.get("scene_ids") or []:
            scene = scenes.get(str(sid))
            if not scene:
                continue
            scene_heard.append(
                listen_scene(state, scene, copies=word_copies, bundle=bundle)
            )
            words_heard += len(scene.get("words") or [])

            me = scene.get("math_episode")
            if isinstance(me, dict) and me.get("cue"):
                ep = append_episode(
                    state,
                    cue=str(me.get("cue") or ""),
                    surface_attempt=str(me.get("correct") or ""),
                    correct=str(me.get("correct") or ""),
                    lattice_id=SCHEMA_MATH,
                    concept_id=str(me.get("concept_id") or "") or None,
                    scene=str(me.get("scene") or sid),
                    bundle=bundle,
                    episode_source="ingest",
                )
                if ep:
                    lesson_math_eps += 1
                    math_episodes += 1

        extra_words = list(lesson.get("extra_words") or [])
        for w in extra_words:
            listen_word(state, w, copies=word_copies, bundle=bundle)
            words_heard += 1

        role_links = list(lesson.get("role_links") or [])
        minted = mint_episode_links(
            lattices,
            lattice_id=SCHEMA_MATH,
            links=role_links,
            copies=link_copies,
        )
        links_minted += len(minted)

        sleep_rep = None
        if sleep_after_each_lesson and (scene_heard or role_links or lesson_math_eps):
            sleep_rep = run_sleep(state, bundle)

        lesson_reports.append(
            {
                "id": lesson.get("id"),
                "title": lesson.get("title"),
                "scenes": len(scene_heard),
                "math_episodes": lesson_math_eps,
                "role_links": len(role_links),
                "sleep": sleep_rep,
            }
        )

    probes: list[dict[str, Any]] = []
    lat = memory_lattices(state).get(SCHEMA_MATH) or {}
    dec = decode_f0_lattice(lat) if lat.get("cells") else {}

    for row in manifest.get("probe") or []:
        kind = str(row.get("kind") or "l2")
        if kind == "l2":
            word = str(row.get("word") or "")
            expect = str(row.get("expect") or f"lang.word.{word}")
            votes, shard = concept_votes_l2(state, expect)
            ok = votes >= int(row.get("min_votes") or 1)
            probes.append(
                {
                    "kind": kind,
                    "word": word,
                    "expect": expect,
                    "votes": votes,
                    "shard": shard,
                    "pass": ok,
                }
            )
        elif kind == "math_f0":
            cue = str(row.get("cue") or "")
            expect = str(row.get("expect") or "")
            ranked = rank_cue_on_f0(dec, cue, bundle=bundle)
            top = ranked[0][0] if ranked else None
            top3 = [r[0] for r in ranked[:3]]
            ok = top == expect or expect in top3
            probes.append(
                {
                    "kind": kind,
                    "cue": cue,
                    "expect": expect,
                    "top": top,
                    "top3": top3,
                    "pass": ok,
                }
            )
        elif kind == "scene":
            sid = str(row.get("scene_id") or "")
            expect_words = [str(w) for w in (row.get("expect_words") or [])]
            min_cv = int(row.get("min_c_votes") or 1)
            recalled = {r["word"]: r["c_votes"] for r in recall_words_for_scene(state, sid)}
            missing = [w for w in expect_words if recalled.get(w, 0) < min_cv]
            probes.append(
                {
                    "kind": kind,
                    "scene_id": sid,
                    "expect_words": expect_words,
                    "recalled": recalled,
                    "missing": missing,
                    "pass": not missing,
                }
            )

    passed = sum(1 for p in probes if p.get("pass"))
    total = len(probes)
    threshold = float(manifest.get("probe_threshold") or 0.75)
    score = passed / total if total else 0.0

    report: dict[str, Any] = {
        "store_dir": str(store_dir),
        "class_id": manifest.get("class_id"),
        "class_dir": str(class_dir),
        "lesson_filter": list(filter_ids) if filter_ids else None,
        "lessons": lesson_reports,
        "words_heard": words_heard,
        "math_episodes": math_episodes,
        "links_minted": links_minted,
        "probe": probes,
        "probe_score": score,
        "probe_ok": score >= threshold,
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
    p = argparse.ArgumentParser(description="Ingest lang lesson class into agent store")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/lang-ru-math-bridge")
    p.add_argument("--no-persist", action="store_true")
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--word-copies", type=int, default=4)
    p.add_argument(
        "--lesson-ids",
        nargs="+",
        default=None,
        help="Ingest only these lesson ids (e.g. lesson-08-fractions)",
    )
    args = p.parse_args()

    rep = ingest_lang_lesson_class(
        args.store_dir or default_agent_store(),
        args.class_dir,
        lesson_ids=args.lesson_ids,
        sleep_after_each_lesson=not args.no_sleep,
        word_copies=max(1, args.word_copies),
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
