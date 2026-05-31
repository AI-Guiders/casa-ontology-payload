#!/usr/bin/env python3
"""Cold-path lexicon ingest on lexicon_miss (offline headwords v0; MCP later)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.tick.predictor import l2_has_word
from casa.prisms.memory.ru_lexicon import ingest_ru_lex_batch, read_headwords
from casa.prisms.memory.segment import norm_word
from casa.prisms.shared.store_layout import field_state_path

LEXICON_MISS_LOG = "lexicon_miss.ndjson"


def append_lexicon_miss_log(log_path: Path, entry: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def store_locale(state: dict) -> str:
    loc = (state.get("store") or {}).get("locale")
    if loc:
        return str(loc).lower()
    cfg = state.get("l2_sharding") or {}
    return str(cfg.get("locale") or "ru").lower()


def lookup_offline_headwords(headwords_path: Path, words: list[str]) -> list[str]:
    """Simulate dictionary lookup: only words listed in offline headword file."""
    available = set(read_headwords(headwords_path))
    out: list[str] = []
    for w in words:
        n = norm_word(w)
        if n and n in available:
            out.append(n)
    return list(dict.fromkeys(out))


def cold_ingest_lexicon(
    state: dict,
    words: list[str],
    *,
    locale: str | None = None,
    copies: int = 3,
    configure: bool = False,
    source: str = "offline_headwords",
) -> dict[str, Any]:
    loc = (locale or store_locale(state)).lower()
    unique = list(dict.fromkeys(norm_word(w) for w in words if norm_word(w)))
    if not unique:
        return {
            "locale": loc,
            "source": source,
            "words_requested": len(words),
            "words_ingested": 0,
            "skipped": [],
        }

    if loc.startswith("en"):
        from casa.prisms.memory.en_lexicon import ingest_en_lex_batch

        stats = ingest_en_lex_batch(state, unique, copies=copies, configure=configure)
        ingested = int(stats.get("en_concepts_on_field") or 0)
    else:
        stats = ingest_ru_lex_batch(state, unique, copies=copies, configure=configure)
        ingested = int(stats.get("ru_concepts_on_field") or 0)

    return {
        "locale": loc,
        "source": source,
        "words_requested": len(words),
        "words_unique": len(unique),
        "words_ingested": ingested,
        "field_version": stats.get("field_version"),
        "shard_histogram": stats.get("shard_histogram"),
    }


def process_lexicon_misses(
    state: dict,
    misses: list[dict[str, Any]],
    *,
    store_dir: Path | None = None,
    headwords_path: Path | None = None,
    locale: str | None = None,
    copies: int = 3,
    source: str = "offline_headwords",
) -> dict[str, Any]:
    """Ingest words from lexicon_miss queue (cold path, not hot predict)."""
    words: list[str] = []
    for item in misses:
        w = norm_word(str(item.get("word") or item.get("prefix") or item.get("cue") or ""))
        if w:
            words.append(w)
    words = list(dict.fromkeys(words))

    skipped: list[str] = []
    if headwords_path is not None:
        resolved = lookup_offline_headwords(headwords_path, words)
        skipped = [w for w in words if w not in set(resolved)]
        words = resolved

    result = cold_ingest_lexicon(
        state,
        words,
        locale=locale,
        copies=copies,
        configure=False,
        source=source,
    )
    result["skipped_not_in_dictionary"] = skipped
    if store_dir is not None and (ingest_report := result.get("shard_histogram")):
        from casa.prisms.shared.nca_registry import merge_pending

        merge_pending(store_dir, list(ingest_report.keys()))
    return result


def log_cold_ingest(
    store_dir: Path,
    *,
    misses: list[dict[str, Any]],
    ingest_report: dict[str, Any],
    source: str = "offline_headwords",
) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "misses": misses,
        "ingest": ingest_report,
    }
    append_lexicon_miss_log(store_dir / LEXICON_MISS_LOG, entry)


def main() -> None:
    p = argparse.ArgumentParser(description="Cold ingest words after lexicon_miss (v0 offline)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--words", nargs="*", default=[])
    p.add_argument("--words-file", type=Path, default=None)
    p.add_argument("--headwords", type=Path, default=None, help="Offline dictionary file (lookup filter)")
    p.add_argument("--locale", default=None, help="ru | en (default: from store)")
    p.add_argument("--copies", type=int, default=3)
    p.add_argument("--write", action="store_true", help="Persist field_state.json")
    p.add_argument("--from-predict", type=Path, default=None, help="JSON predict output with lexicon_miss")
    args = p.parse_args()

    store = args.store_dir.resolve()
    fs_path = field_state_path(store)
    state = load_field_state(fs_path)
    if not state:
        raise SystemExit(f"field_state missing: {fs_path} (boot store with field_state for cold ingest v0)")

    misses: list[dict[str, Any]] = []
    words: list[str] = list(args.words)
    if args.words_file:
        words.extend(read_headwords(args.words_file))
    if args.from_predict:
        pred = json.loads(args.from_predict.read_text(encoding="utf-8"))
        lm = pred.get("lexicon_miss") or {}
        if lm.get("miss"):
            misses.append(lm)
            words.append(str(lm.get("prefix") or pred.get("cue") or ""))

    words = list(dict.fromkeys(norm_word(w) for w in words if norm_word(w)))
    if not words and not misses:
        raise SystemExit("provide --words, --words-file, or --from-predict with lexicon_miss")

    if not misses:
        misses = [{"prefix": w, "word": w, "reason": "cli"} for w in words]

    report = process_lexicon_misses(
        state,
        misses,
        store_dir=store,
        headwords_path=args.headwords,
        locale=args.locale,
        copies=args.copies,
    )
    log_cold_ingest(store, misses=misses, ingest_report=report)

    if args.write:
        save_field_state(fs_path, state)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
