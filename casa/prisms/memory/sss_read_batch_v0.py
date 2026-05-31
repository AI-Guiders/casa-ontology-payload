#!/usr/bin/env python3
"""Batch read folder of .txt tales — one sleep at end, vocabulary growth report."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, save_state  # type: ignore
from sss_text_ingest_v0 import ingest_text  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique, extract_words, norm_text  # type: ignore
from sss_vocab_v0 import punct_votes_from_field, word_votes_from_field  # type: ignore


def _save_progress_sidecar(store_path: Path, prog: dict) -> None:
    """Tiny progress file (~KB) without rewriting full field_state."""
    sidecar = store_path.with_name("batch_progress.json")
    sidecar.write_text(json.dumps(prog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def read_batch(
    state: dict,
    corpus_dir: Path,
    *,
    bukvar_bundle: dict | None,
    listen_copies: int = 2,
    sleep_once: bool = True,
    min_word_len: int = 1,
    use_field: bool = False,
    store_path: Path | None = None,
    checkpoint_every: int = 25,
    resume: bool = False,
    compact_save: bool = True,
    progress_sidecar: bool = True,
) -> dict[str, Any]:
    from sss_text_listen_field_v0 import ingest_text_field  # type: ignore

    ingest_fn = ingest_text_field if use_field else ingest_text
    files = sorted(corpus_dir.glob("*.txt"))
    prog = state.setdefault("batch_progress", {})
    done_files = set(prog.get("files") or []) if resume else set()
    before_w = word_votes_from_field(state)
    before_p = punct_votes_from_field(state)
    tales: list[dict] = []
    all_words: set[str] = set()
    all_punct: set[str] = set()
    skipped = len(done_files)
    if resume and skipped:
        print(f"[batch] resume: skip {skipped} already done, continue from next tale", flush=True)

    t0 = time.perf_counter()
    last_cp = t0
    new_count = 0

    for i, fp in enumerate(files, 1):
        if fp.name in done_files:
            continue
        tale_t0 = time.perf_counter()
        text = norm_text(fp.read_text(encoding="utf-8"))
        if not text.strip():
            continue
        all_words.update(extract_words(text, min_len=min_word_len))
        all_punct.update(extract_punctuation_unique(text))
        rep = ingest_fn(
            state,
            text,
            title=f"Читаем: {fp.name}",
            bukvar_bundle=bukvar_bundle,
            listen_copies=listen_copies,
            sleep=False,
            min_word_len=min_word_len,
        )
        tales.append(
            {
                "file": fp.name,
                "session_id": rep.get("session_id"),
                "words_unique": len(rep.get("extract", {}).get("words_unique") or []),
                "discovered": len(rep.get("extract", {}).get("discovered") or []),
                "ingest_mode": rep.get("ingest_mode"),
            }
        )
        done_files.add(fp.name)
        new_count += 1
        prog["files"] = sorted(done_files)
        prog["last_file"] = fp.name
        prog["field_version"] = state.get("field_version")
        tale_s = time.perf_counter() - tale_t0
        if new_count == 1 or new_count % 5 == 0 or len(done_files) == len(files):
            elapsed = time.perf_counter() - t0
            print(
                f"[batch] {len(done_files)}/{len(files)} {fp.name} fv={state.get('field_version')} "
                f"new={new_count} tale={tale_s:.1f}s elapsed={elapsed:.0f}s",
                flush=True,
            )
        if store_path and progress_sidecar and len(tales) % 10 == 0:
            _save_progress_sidecar(store_path, dict(prog))
        if store_path and checkpoint_every > 0 and len(tales) % checkpoint_every == 0:
            save_state(store_path, state, compact=compact_save)
            now = time.perf_counter()
            mb = store_path.stat().st_size / 1e6 if store_path.is_file() else 0
            print(
                f"[checkpoint] {len(done_files)} files store={mb:.1f}MB save={now - last_cp:.1f}s",
                flush=True,
            )
            last_cp = now

    sleep_report = None
    if sleep_once and tales and bukvar_bundle:
        from sss_cylinders_v0 import run_sleep  # type: ignore

        sleep_report = run_sleep(state, bukvar_bundle)

    after_w = word_votes_from_field(state)
    after_p = punct_votes_from_field(state)
    for fp in files:
        t = norm_text(fp.read_text(encoding="utf-8"))
        all_words.update(extract_words(t, min_len=min_word_len))
        all_punct.update(extract_punctuation_unique(t))

    return {
        "batch_id": f"batch-{int(time.time() * 1000) % 10_000_000}",
        "corpus_dir": str(corpus_dir),
        "tales_read": len(tales),
        "tales": tales,
        "sleep": sleep_report,
        "vocabulary": {
            "words_unique_corpus": sorted(all_words),
            "words_on_field": sum(1 for w in all_words if after_w.get(w, 0) > 0),
            "punct_on_field": sum(1 for m in all_punct if after_p.get(m, 0) > 0),
            "new_words_this_batch": [w for w in all_words if before_w.get(w, 0) == 0 and after_w.get(w, 0) > 0],
            "reinforced_words": [w for w in all_words if before_w.get(w, 0) > 0],
        },
        "use_field": use_field,
        "field_version": state.get("field_version"),
        "resumed_from": len(done_files) - len(tales),
        "checkpoint_files": sorted(done_files),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--listen-copies", type=int, default=2)
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--field", action="store_true", help="Phase B: field word competition")
    p.add_argument("--resume", action="store_true", help="Skip files already in batch_progress")
    p.add_argument(
        "--checkpoint-every",
        type=int,
        default=25,
        help="Save field_state every N new tales (0 = RAM only until final save)",
    )
    p.add_argument("--no-progress-sidecar", action="store_true", help="Skip tiny batch_progress.json updates")
    p.add_argument("--pretty-save", action="store_true", help="Indented JSON (slow); default is compact")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    if args.checkpoint_every == 0:
        print("[batch] RAM-only mode: field_state saved once at end", flush=True)
    bukvar = json.loads(args.bukvar.read_text(encoding="utf-8")) if args.bukvar.exists() else None
    store_path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(store_path))
    report = read_batch(
        state,
        args.corpus_dir,
        bukvar_bundle=bukvar,
        listen_copies=max(1, args.listen_copies),
        sleep_once=not args.no_sleep,
        use_field=args.field,
        store_path=store_path,
        checkpoint_every=max(0, args.checkpoint_every),
        resume=args.resume,
        compact_save=not args.pretty_save,
        progress_sidecar=not args.no_progress_sidecar,
    )
    save_state(store_path, state, compact=not args.pretty_save)
    if not args.no_progress_sidecar:
        _save_progress_sidecar(store_path, state.get("batch_progress") or {})
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
