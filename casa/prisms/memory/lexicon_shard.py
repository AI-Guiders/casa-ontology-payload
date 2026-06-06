#!/usr/bin/env python3
"""L2 word lattice sharding: route words across a network of memory grids."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.prism_ids import PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL
from casa.domain.prism_wire import normalize_prisms, prism_memory, prism_hippo, prism_control, set_active_prism

import unicodedata
import zlib
from collections.abc import Iterable
from typing import Any

from casa.prisms.shared.lattice_names_v1 import lexicon_shard_id, parse_lexicon_range_lattice, parse_lexicon_shard
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.stack import decode_lattice, lattice_digest

LEGACY_L2 = "L2_word"
L2_SHARD_PREFIX = "L2_word_"
DEFAULT_NUM_SHARDS = 64
L2_Z_LEVEL = 2
L2_CONCEPT_PREFIX = "lang.word."
DEFAULT_LATTICE_SIZE = 32

# Russian dictionary letter order (pedagogical / standard lexicographic).
RU_DICT_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

SHARD_MODE_HASH = "hash"
SHARD_MODE_LEXICOGRAPHIC = "lexicographic"
DEFAULT_SHARD_MODE = SHARD_MODE_LEXICOGRAPHIC

SHARD_NAMING_NUMERIC = "numeric"
SHARD_NAMING_CORPUS_RANGE = "corpus_range"
DEFAULT_SHARD_NAMING = SHARD_NAMING_NUMERIC

LEX_PLAN_ALPHA = "alpha"
LEX_PLAN_CORPUS_QUANTILE = "corpus_quantile"
DEFAULT_LEX_PLAN = LEX_PLAN_CORPUS_QUANTILE


def norm_word(word: str) -> str:
    return unicodedata.normalize("NFC", (word or "").strip().lower())


L2_EN_SHARD_PREFIX = "L2_en_word_"
DEFAULT_EN_NUM_SHARDS = 16


def is_l2_en_word_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    if lid.startswith(L2_EN_SHARD_PREFIX):
        return True
    parsed = parse_lexicon_shard(lid)
    return parsed is not None and parsed[0] == "en"


def en_l2_shard_id(word: str, *, num_shards: int = DEFAULT_EN_NUM_SHARDS) -> str:
    w = norm_word(word)
    idx = zlib.crc32(w.encode("utf-8")) % max(1, num_shards)
    return lexicon_shard_id("en", idx)


def route_en_l2_lattice(state: dict, word: str) -> str:
    cfg = sharding_config(state)
    en_cfg = cfg.get("en") or {}
    num = int(en_cfg.get("num_shards") or DEFAULT_EN_NUM_SHARDS)
    shard = en_l2_shard_id(word, num_shards=num)
    ensure_l2_lattice(state, shard)
    register_word_shard(state, word, shard)
    return shard


def l2_en_word_lattice_ids(state: dict) -> list[str]:
    state = ensure_prisms(state)
    return sorted(lid for lid in memory_lattices(state) if is_l2_en_word_lattice(lid))


def l2_lexicon_lattice_ids(state: dict) -> list[str]:
    return sorted(set(l2_word_lattice_ids(state)) | set(l2_en_word_lattice_ids(state)))


def is_nca_trainable_lattice(lattice_id: str) -> bool:
    """RU/EN L2 shards (and legacy L2_word) — eligible for per-shard NCA repair."""
    return is_l2_word_lattice(lattice_id) or is_l2_en_word_lattice(lattice_id)


def is_l2_word_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    if lid == LEGACY_L2 or lid.startswith(L2_SHARD_PREFIX):
        return True
    parsed = parse_lexicon_shard(lid)
    if parsed is not None and parsed[0] in ("ru", "en"):
        return True
    range_parsed = parse_lexicon_range_lattice(lid)
    return range_parsed is not None and range_parsed[0] in ("ru", "en", "uk", "be")


def first_letter_index(char: str) -> int:
    """0..len(alpha)-1 for dictionary letters; len(alpha) = other."""
    try:
        return RU_DICT_ALPHABET.index(char)
    except ValueError:
        return len(RU_DICT_ALPHABET)


def lex_sort_key(word: str) -> tuple[int, str]:
    """Total lexicographic key (dictionary order) for sorting headwords."""
    w = norm_word(word)
    if not w:
        return (len(RU_DICT_ALPHABET) + 1, "")
    return (first_letter_index(w[0]), w)


def lexicon_range_slug_part(word: str, *, max_len: int = 24) -> str:
    """Filesystem-safe slug from a headword (Cyrillic + hyphen allowed)."""
    s = norm_word(word)
    chars: list[str] = []
    for ch in s:
        if ch.isalnum() or ch == "-":
            chars.append(ch)
        elif ch.isspace():
            chars.append("-")
    out = "".join(chars).strip("-")
    if not out:
        return "empty"
    return out[:max_len] if len(out) > max_len else out


def lexicon_range_slug(word_lo: str, word_hi: str) -> str:
    lo = lexicon_range_slug_part(word_lo)
    hi = lexicon_range_slug_part(word_hi)
    if lo == hi:
        return lo
    return f"{lo}-{hi}"


def lexicon_corpus_range_lattice_id(locale: str, word_lo: str, word_hi: str) -> str:
    loc = str(locale).strip().lower().replace("_", "-").split("-", 1)[0]
    return f"lexicon-{loc}-{lexicon_range_slug(word_lo, word_hi)}"


def attach_corpus_range_shard_ids(
    ranges: list[dict[str, Any]],
    *,
    locale: str = "ru",
) -> list[dict[str, Any]]:
    """Fill shard_id on each quantile range row (dictionary lo–hi slug)."""
    out: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for row in ranges:
        r = dict(row)
        lo = str(r.get("word_lo") or "")
        hi = str(r.get("word_hi") or "")
        base = lexicon_corpus_range_lattice_id(locale, lo, hi)
        if base in seen:
            seen[base] += 1
            r["shard_id"] = f"{base}-{seen[base]}"
        else:
            seen[base] = 0
            r["shard_id"] = base
        out.append(r)
    return out


def corpus_range_shard_id(cfg: dict[str, Any], shard_index: int) -> str | None:
    ranges = cfg.get("letter_ranges") or []
    if shard_index < 0 or shard_index >= len(ranges):
        return None
    row = ranges[shard_index]
    sid = row.get("shard_id")
    if sid:
        return str(sid)
    lo = str(row.get("word_lo") or "")
    hi = str(row.get("word_hi") or "")
    if lo or hi:
        return lexicon_corpus_range_lattice_id(str(cfg.get("locale") or "ru"), lo, hi)
    return None


def build_semantic_l2_rename_map(cfg: dict[str, Any], *, locale: str = "ru") -> dict[str, str]:
    """Map legacy numeric shard ids → corpus-range lexicon ids."""
    ranges = attach_corpus_range_shard_ids(list(cfg.get("letter_ranges") or []), locale=locale)
    mapping: dict[str, str] = {}
    for row in ranges:
        idx = int(row.get("shard", -1))
        if idx < 0:
            continue
        new_id = str(row.get("shard_id") or "")
        if not new_id:
            continue
        for old in (f"{L2_SHARD_PREFIX}{idx:02d}", lexicon_shard_id(locale, idx)):
            if old != new_id:
                mapping[old] = new_id
    return mapping


def _range_label(lo: str, hi: str, *, max_len: int = 40) -> str:
    if not lo and not hi:
        return "∅"
    if lo == hi:
        return lo
    text = f"{lo}–{hi}"
    if len(text) <= max_len:
        return text
    return f"{lo[:14]}…–{hi[:14]}"


def attested_initial_letters(words: Iterable[str]) -> list[str]:
    """First characters that actually start headwords in corpus (dictionary order)."""
    seen: set[str] = set()
    for w in sorted({norm_word(x) for x in words if norm_word(x)}, key=lex_sort_key):
        seen.add(w[0])
    return sorted(seen, key=lambda c: first_letter_index(c) if c in RU_DICT_ALPHABET else len(RU_DICT_ALPHABET) + ord(c))


def initial_letter_counts(words: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for w in words:
        n = norm_word(w)
        if n:
            counts[n[0]] = counts.get(n[0], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: first_letter_index(kv[0]) if kv[0] in RU_DICT_ALPHABET else 999))


def build_lex_ranges_from_corpus(
    words: Iterable[str],
    *,
    num_shards: int,
) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    """
    Dictionary-order shards with ~equal word counts (quantile bins).
    Only headwords present in corpus; no empty «ь/ы as first letter» shelves.
    """
    unique = sorted({norm_word(w) for w in words if norm_word(w)}, key=lex_sort_key)
    n = len(unique)
    counts = initial_letter_counts(unique)
    starts: list[str] = []
    ranges: list[dict[str, Any]] = []

    for shard in range(max(1, num_shards)):
        if n == 0:
            starts.append("")
            ranges.append(
                {
                    "shard": shard,
                    "plan": LEX_PLAN_CORPUS_QUANTILE,
                    "word_lo": "",
                    "word_hi": "",
                    "label": "∅",
                    "word_count": 0,
                    "initial_letters": [],
                }
            )
            continue

        i0 = (shard * n) // num_shards
        i1 = ((shard + 1) * n) // num_shards
        if i0 >= n:
            starts.append(unique[-1])
            ranges.append(
                {
                    "shard": shard,
                    "plan": LEX_PLAN_CORPUS_QUANTILE,
                    "word_lo": "",
                    "word_hi": "",
                    "label": "∅",
                    "word_count": 0,
                    "initial_letters": [],
                }
            )
            continue

        starts.append(unique[i0])
        word_count = max(0, i1 - i0)
        if word_count == 0:
            lo = hi = unique[min(i0, n - 1)]
            letters: list[str] = []
        else:
            lo = unique[i0]
            hi = unique[i1 - 1]
            letters = sorted({w[0] for w in unique[i0:i1]})

        ranges.append(
            {
                "shard": shard,
                "plan": LEX_PLAN_CORPUS_QUANTILE,
                "word_lo": lo,
                "word_hi": hi,
                "label": _range_label(lo, hi) if word_count else "∅",
                "word_count": word_count,
                "initial_letters": letters,
            }
        )

    return ranges, starts, counts


def configure_lex_sharding(cfg: dict[str, Any], words: Iterable[str], *, num_shards: int | None = None) -> None:
    """Install corpus-quantile plan into l2_sharding config."""
    n = int(num_shards if num_shards is not None else cfg.get("num_shards") or DEFAULT_NUM_SHARDS)
    ranges, starts, letter_counts = build_lex_ranges_from_corpus(words, num_shards=n)
    cfg["num_shards"] = n
    cfg["lex_plan"] = LEX_PLAN_CORPUS_QUANTILE
    cfg["letter_ranges"] = ranges
    cfg["lex_shard_starts"] = starts
    cfg["initial_letter_counts"] = letter_counts


def build_letter_ranges(num_shards: int) -> list[dict[str, Any]]:
    """
    Fallback: partition alphabet string into num_shards (may include empty letter slices).
    Prefer configure_lex_sharding() with real headwords.
    """
    n = len(RU_DICT_ALPHABET)
    span = n + 1  # +1 bucket for non-dictionary first characters
    ranges: list[dict[str, Any]] = []
    for shard in range(max(1, num_shards)):
        lo = (shard * span) // num_shards
        hi = ((shard + 1) * span) // num_shards
        if lo >= hi:
            label = "∅"
            first_lo, first_hi = "{", "{"
        elif hi <= n:
            first_lo = RU_DICT_ALPHABET[lo]
            first_hi = RU_DICT_ALPHABET[hi - 1]
            label = first_lo if first_lo == first_hi else f"{first_lo}–{first_hi}"
        elif lo >= n:
            first_lo, first_hi = "{", "~"
            label = "прочее"
        else:
            first_lo = RU_DICT_ALPHABET[lo]
            first_hi = "~"
            label = f"{first_lo}–прочее"
        ranges.append(
            {
                "shard": shard,
                "plan": LEX_PLAN_ALPHA,
                "letter_lo": lo,
                "letter_hi_excl": hi,
                "first_lo": first_lo,
                "first_hi": first_hi,
                "label": label,
            }
        )
    return ranges


def letter_range_for_shard(shard: int, ranges: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in ranges:
        if int(row.get("shard", -1)) == shard:
            return row
    return None


def sharding_config(state: dict) -> dict[str, Any]:
    state = ensure_prisms(state)
    cfg = dict(state.get("l2_sharding") or {})
    cfg.setdefault("enabled", True)
    cfg.setdefault("num_shards", DEFAULT_NUM_SHARDS)
    cfg.setdefault("legacy_lattice", LEGACY_L2)
    cfg.setdefault("shard_prefix", L2_SHARD_PREFIX)
    cfg.setdefault("shard_naming", DEFAULT_SHARD_NAMING)
    cfg.setdefault("locale", "ru")
    cfg.setdefault("mode", DEFAULT_SHARD_MODE)
    cfg.setdefault("lex_plan", DEFAULT_LEX_PLAN)
    cfg.setdefault("word_index", {})
    num = int(cfg.get("num_shards") or DEFAULT_NUM_SHARDS)
    if cfg.get("mode", DEFAULT_SHARD_MODE) == SHARD_MODE_LEXICOGRAPHIC:
        ranges = cfg.get("letter_ranges")
        if not ranges or len(ranges) != num:
            cfg["letter_ranges"] = build_letter_ranges(num)
            cfg["lex_plan"] = LEX_PLAN_ALPHA
    state["l2_sharding"] = cfg
    return cfg


def l2_shard_index_hash(word: str, *, num_shards: int) -> int:
    w = norm_word(word)
    return zlib.crc32(w.encode("utf-8")) % max(1, num_shards)


def l2_shard_index_lex_quantile(
    word: str,
    *,
    num_shards: int,
    shard_starts: list[str],
) -> int:
    w = norm_word(word)
    if not w or not shard_starts:
        return 0
    key = lex_sort_key(w)
    shard = 0
    for s in range(1, min(num_shards, len(shard_starts))):
        if lex_sort_key(shard_starts[s]) <= key:
            shard = s
        else:
            break
    return shard


def l2_shard_index_lex_alpha(
    word: str,
    *,
    num_shards: int,
    letter_ranges: list[dict[str, Any]] | None = None,
) -> int:
    w = norm_word(word)
    if not w:
        return 0
    ranges = letter_ranges or build_letter_ranges(num_shards)
    ci = first_letter_index(w[0])
    for row in ranges:
        lo = int(row["letter_lo"])
        hi = int(row["letter_hi_excl"])
        if lo <= ci < hi:
            return int(row["shard"])
    return max(0, num_shards - 1)


def l2_shard_index_lex(
    word: str,
    *,
    num_shards: int,
    letter_ranges: list[dict[str, Any]] | None = None,
    lex_plan: str = DEFAULT_LEX_PLAN,
    shard_starts: list[str] | None = None,
) -> int:
    ranges = letter_ranges or []
    plan = lex_plan
    if ranges and str(ranges[0].get("plan") or "") == LEX_PLAN_CORPUS_QUANTILE:
        plan = LEX_PLAN_CORPUS_QUANTILE
    if plan == LEX_PLAN_CORPUS_QUANTILE:
        starts = shard_starts or [str(r.get("word_lo") or "") for r in ranges]
        if starts and len(starts) >= num_shards:
            return l2_shard_index_lex_quantile(word, num_shards=num_shards, shard_starts=starts)
    return l2_shard_index_lex_alpha(word, num_shards=num_shards, letter_ranges=letter_ranges)


def l2_shard_index(
    word: str,
    *,
    num_shards: int,
    mode: str = DEFAULT_SHARD_MODE,
    letter_ranges: list[dict[str, Any]] | None = None,
    lex_plan: str = DEFAULT_LEX_PLAN,
    shard_starts: list[str] | None = None,
) -> int:
    if mode == SHARD_MODE_HASH:
        return l2_shard_index_hash(word, num_shards=num_shards)
    return l2_shard_index_lex(
        word,
        num_shards=num_shards,
        letter_ranges=letter_ranges,
        lex_plan=lex_plan,
        shard_starts=shard_starts,
    )


def l2_shard_id(
    word: str,
    *,
    num_shards: int = DEFAULT_NUM_SHARDS,
    mode: str = DEFAULT_SHARD_MODE,
    letter_ranges: list[dict[str, Any]] | None = None,
    lex_plan: str = DEFAULT_LEX_PLAN,
    shard_starts: list[str] | None = None,
    shard_prefix: str | None = None,
    sharding_cfg: dict[str, Any] | None = None,
) -> str:
    idx = l2_shard_index(
        word,
        num_shards=num_shards,
        mode=mode,
        letter_ranges=letter_ranges,
        lex_plan=lex_plan,
        shard_starts=shard_starts,
    )
    cfg = sharding_cfg or {}
    if str(cfg.get("shard_naming") or DEFAULT_SHARD_NAMING) == SHARD_NAMING_CORPUS_RANGE:
        sid = corpus_range_shard_id(cfg, idx)
        if sid:
            return sid
    prefix = shard_prefix or str(cfg.get("shard_prefix") or L2_SHARD_PREFIX)
    if prefix.startswith("lexicon-"):
        locale = prefix.removeprefix("lexicon-").rstrip("-")
        return lexicon_shard_id(locale, idx)
    return f"{prefix}{idx:02d}"


def empty_l2_lattice(*, width: int = DEFAULT_LATTICE_SIZE, height: int = DEFAULT_LATTICE_SIZE) -> dict:
    n = width * height
    return {
        "z_level": L2_Z_LEVEL,
        "width": width,
        "height": height,
        "cells": [[] for _ in range(n)],
        "concept_prefix": L2_CONCEPT_PREFIX,
        "shard": True,
    }


def ensure_l2_lattice(state: dict, lattice_id: str) -> dict:
    """Create shard lattice if missing; sync prism_memory + sss.lattices."""
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    if lattice_id not in lattices:
        lattices[lattice_id] = empty_l2_lattice()
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lattices[lattice_id]


def register_word_shard(state: dict, word: str, lattice_id: str) -> None:
    cfg = sharding_config(state)
    idx = dict(cfg.get("word_index") or {})
    idx[norm_word(word)] = lattice_id
    cfg["word_index"] = idx
    state["l2_sharding"] = cfg


def resolve_l2_lattice_for_read(state: dict, word: str) -> str:
    """Route for read/surface: index → legacy monolith → new shard."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    w = norm_word(word)
    if not w:
        return str(cfg.get("legacy_lattice") or LEGACY_L2)
    idx = cfg.get("word_index") or {}
    if w in idx:
        return str(idx[w])
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L2)
    cid = f"{L2_CONCEPT_PREFIX}{w}"
    lat = memory_lattices(state).get(legacy) or {}
    dec = decode_lattice(lat, min_votes=1)
    if any(str(c.get("concept_id")) == cid for c in dec.get("concepts") or []):
        register_word_shard(state, w, legacy)
        return legacy
    return route_l2_lattice(state, w)


def route_l2_lattice(state: dict, word: str) -> str:
    """Pick L2 shard for a word (index → lex/hash → legacy fallback)."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    w = norm_word(word)
    if not w:
        return str(cfg.get("legacy_lattice") or LEGACY_L2)
    idx = cfg.get("word_index") or {}
    if w in idx:
        return str(idx[w])
    if not cfg.get("enabled", True):
        return str(cfg.get("legacy_lattice") or LEGACY_L2)
    num = int(cfg.get("num_shards") or DEFAULT_NUM_SHARDS)
    mode = str(cfg.get("mode") or DEFAULT_SHARD_MODE)
    ranges = cfg.get("letter_ranges") if mode == SHARD_MODE_LEXICOGRAPHIC else None
    shard = l2_shard_id(
        w,
        num_shards=num,
        mode=mode,
        letter_ranges=ranges,
        lex_plan=str(cfg.get("lex_plan") or DEFAULT_LEX_PLAN),
        shard_starts=cfg.get("lex_shard_starts"),
        shard_prefix=str(cfg.get("shard_prefix") or L2_SHARD_PREFIX),
        sharding_cfg=cfg,
    )
    ensure_l2_lattice(state, shard)
    register_word_shard(state, w, shard)
    return shard


def l2_word_lattice_ids(state: dict) -> list[str]:
    """All L2 layers: legacy monolith + shards (sorted)."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L2)
    ids = {lid for lid in memory_lattices(state) if is_l2_word_lattice(lid)}
    ids.add(legacy)
    return sorted(ids, key=lambda x: (0 if x == legacy else 1, x))


def lattice_digest_l2_network(
    state: dict,
    *,
    prefix: str = L2_CONCEPT_PREFIX,
    min_votes: int = 1,
) -> list[tuple[str, int]]:
    """Merge concept digests across RU + EN L2 shards."""
    merged: dict[str, int] = {}
    for lid in l2_lexicon_lattice_ids(state):
        lat = memory_lattices(state).get(lid) or {}
        dec = decode_lattice(lat, min_votes=min_votes)
        for cid, votes in lattice_digest(dec, prefix=prefix):
            merged[cid] = merged.get(cid, 0) + votes
    return sorted(merged.items(), key=lambda x: (-x[1], x[0]))


def concept_votes_l2(state: dict, concept_id: str) -> tuple[int, str | None]:
    """Votes for lang.word.* on the shard that holds the word (or legacy)."""
    if not concept_id.startswith(L2_CONCEPT_PREFIX):
        return 0, None
    word = concept_id[len(L2_CONCEPT_PREFIX) :]
    lid = resolve_l2_lattice_for_read(state, word)
    lat = memory_lattices(state).get(lid) or {}
    dec = decode_lattice(lat, min_votes=1)
    for c in dec.get("concepts") or []:
        if str(c.get("concept_id")) == concept_id:
            return int(c.get("votes") or 0), lid
    legacy = str(sharding_config(state).get("legacy_lattice") or LEGACY_L2)
    if lid != legacy:
        lat = memory_lattices(state).get(legacy) or {}
        dec = decode_lattice(lat, min_votes=1)
        for c in dec.get("concepts") or []:
            if str(c.get("concept_id")) == concept_id:
                return int(c.get("votes") or 0), legacy
    return 0, lid


def nca_model_registry(state: dict) -> dict[str, str]:
    nca = state.setdefault("nca", {})
    models = dict(nca.get("models") or {})
    nca["models"] = models
    return models


def set_nca_model(state: dict, lattice_id: str, model_path: str) -> None:
    reg = nca_model_registry(state)
    reg[lattice_id] = model_path


def _shard_index_from_lattice_id(
    lattice_id: str,
    letter_ranges: list[dict[str, Any]] | None = None,
) -> int | None:
    if letter_ranges:
        for row in letter_ranges:
            if str(row.get("shard_id") or "") == lattice_id:
                return int(row.get("shard", -1))
    parsed = parse_lexicon_shard(lattice_id)
    if parsed is not None and parsed[0] == "ru":
        return parsed[1]
    if not lattice_id.startswith(L2_SHARD_PREFIX):
        return None
    try:
        return int(lattice_id[len(L2_SHARD_PREFIX) :])
    except ValueError:
        return None


def lattice_vocab_size(lattice: dict) -> int:
    """Unique token count on a lattice (ltm v0 vocab limit is u16)."""
    from casa.prisms.memory.nca_codec import tokens_from_lattice

    return len(tokens_from_lattice(lattice))


def shard_stats(state: dict) -> dict[str, Any]:
    from casa.prisms.memory.nca_codec import tokens_from_lattice

    cfg = sharding_config(state)
    mode = str(cfg.get("mode") or DEFAULT_SHARD_MODE)
    ranges = list(cfg.get("letter_ranges") or [])
    lattices = memory_lattices(state)
    rows: list[dict[str, Any]] = []
    naming = str(cfg.get("shard_naming") or DEFAULT_SHARD_NAMING)
    if naming == SHARD_NAMING_CORPUS_RANGE and ranges:
        for row in ranges:
            sid = int(row.get("shard", -1))
            lid = str(row.get("shard_id") or "")
            if not lid and sid >= 0:
                lid = corpus_range_shard_id(cfg, sid) or f"{cfg.get('shard_prefix', L2_SHARD_PREFIX)}{sid:02d}"
            lat = lattices.get(lid) or {}
            toks = tokens_from_lattice(lat)
            words = sum(1 for t in toks if t.startswith("C:lang.word."))
            rows.append(
                {
                    "lattice_id": lid,
                    "token_count": len(toks),
                    "word_concepts": words,
                    "lex_range": row.get("label"),
                    "lex_word_count": row.get("word_count"),
                }
            )
    else:
        for lid in l2_word_lattice_ids(state):
            lat = lattices.get(lid) or {}
            toks = tokens_from_lattice(lat)
            words = sum(1 for t in toks if t.startswith("C:lang.word."))
            row: dict[str, Any] = {"lattice_id": lid, "token_count": len(toks), "word_concepts": words}
            sid = _shard_index_from_lattice_id(lid, ranges)
            if sid is not None and sid < len(ranges):
                row["lex_range"] = ranges[sid].get("label")
                row["lex_word_count"] = ranges[sid].get("word_count")
            rows.append(row)
    return {
        "enabled": cfg.get("enabled"),
        "mode": mode,
        "lex_plan": cfg.get("lex_plan"),
        "num_shards": cfg.get("num_shards"),
        "legacy_lattice": cfg.get("legacy_lattice"),
        "indexed_words": len(cfg.get("word_index") or {}),
        "attested_initial_letters": list((cfg.get("initial_letter_counts") or {}).keys()),
        "initial_letter_counts": cfg.get("initial_letter_counts"),
        "letter_ranges": ranges if mode == SHARD_MODE_LEXICOGRAPHIC else None,
        "shard_naming": cfg.get("shard_naming"),
        "lattices": rows,
    }


def clear_l2_shards(state: dict, *, keep_legacy: bool = True) -> None:
    """Drop shard lattices and word index (for re-migrate)."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    lattices = memory_lattices(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L2)
    drop = [lid for lid in list(lattices) if is_l2_word_lattice(lid) and lid != legacy]
    for lid in drop:
        del lattices[lid]
    cfg["word_index"] = {}
    state["l2_sharding"] = cfg
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
