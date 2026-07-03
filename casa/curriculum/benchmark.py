#!/usr/bin/env python3
"""NUN-Bench generator — deterministic dangerous-error injection into aligned pairs.

Builds the benchmark from the filtered EMEA pool: for each selected pair ONE side (the
translation) receives ONE injected error of a dangerous class, with full metadata so every
corruption is reproducible from the record alone (apply ``replacement`` at ``char_span``).

  polarity — a negation token is DROPPED («No tome…» → «Tome…») — the classic killer.
  quantity — the first number is deterministically corrupted (×10 / transposition / digit).
  unit     — the first unit token is swapped (mg↔ml, µg→mg, …) — the dose-swap class.
  entity   — a detected drug name is replaced from a fixed pool (TAMIFLU→ABILIFY).

Controls: untouched correct pairs (label=equivalent), including correctly-negating ones.
Canaries: fabricated pairs with invented drug names, routed to the held-out split —
contamination markers for future model-training leaks.

Everything is keyed on blake2 hashes of the pair id — NO randomness, same input → same
benchmark, byte for byte. Split public/heldout is also hash-derived.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

GENERATOR_VERSION = "nunbench-gen-0.3"

# --- deterministic choice ----------------------------------------------------------------


def _h(key: str, salt: str = "") -> int:
    return int.from_bytes(hashlib.blake2b(f"{salt}:{key}".encode("utf-8"), digest_size=8).digest(), "big")


def _pick(seq: list, key: str, salt: str):
    return seq[_h(key, salt) % len(seq)]


# --- injectors: (text, lang, key) -> (corrupted, meta) | None ----------------------------

_NEG_PATTERNS = {
    "en": [r"\bdo not\s+", r"\bdoes not\s+", r"\bnot\s+", r"\bnever\s+"],
    "es": [r"\bno\s+", r"\bnunca\s+"],
}
# Spanish negative concord: dropping «no» while «ningún/nada/…» remains does NOT flip the
# polarity (and reads broken) — such sentences are skipped, not half-corrupted.
_NEG_CONCORD = {
    "en": re.compile(r"\b(no|none|nothing|neither|nor)\b", re.IGNORECASE),
    "es": re.compile(r"\b(ningún|ninguna|ningunos?|nada|nadie|tampoco|jamás|jamas|ni)\b", re.IGNORECASE),
}


def inject_polarity(text: str, lang: str, key: str) -> tuple[str, dict] | None:
    """Drop the negation token — the lost-«не» class. Applies ONLY when the sentence has
    exactly one negation and no negative-concord residue («no … ningún»), so the corruption
    is a clean, unambiguous polarity flip. When the negation opens the sentence («No
    tome…»), the restored capitalization is PART of the replacement (the span swallows the
    next word's first letter), so the record replays exactly."""
    all_hits = [m for pat in _NEG_PATTERNS.get(lang, [])
                for m in re.finditer(pat, text, flags=re.IGNORECASE)]
    if len(all_hits) != 1:
        return None  # zero or multiple negations — not a clean flip
    for pat in _NEG_PATTERNS.get(lang, []):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        residue = text[:m.start()] + text[m.end():]
        if _NEG_CONCORD.get(lang) and _NEG_CONCORD[lang].search(residue):
            return None  # negative concord would survive the drop
        start, end = m.start(), m.end()
        replacement = ""
        if start == 0 and end < len(text):  # «No tome…» → «Tome…»
            replacement = text[end].upper()
            end += 1
        out = text[:start] + replacement + text[end:]
        return out, {"side": "tgt", "class": "polarity", "original": text[start:end],
                     "replacement": replacement, "char_span": [start, end]}
    return None


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _strip_leading_zeros(surface: str) -> str:
    """«03» → «3», «01,5» → «1,5»; a true zero integer part («0,5») is left alone."""
    m = re.match(r"0+(?=\d)", surface)
    return surface[m.end():] if m else surface


def _replace_first_digit(surface: str) -> str:
    d = surface[0]
    nd = str((int(d) + 2) % 10) if d.isdigit() else d
    if nd == "0":
        nd = "3"
    return nd + surface[1:]


def _corrupt_number(surface: str, key: str) -> str | None:
    """A corrupted number must read as a DIFFERENT dose, not as a typo — no variant may
    produce a leading zero («250» → «052»): such a transposition falls back to the
    digit-replacement variant, and the decimal shift strips the zeros it uncovers."""
    variant = _h(key, "qty") % 3
    sep = "," if "," in surface else "." if "." in surface else None
    digits = surface.replace(",", "").replace(".", "")
    if variant == 0:  # ×10 — decimal shift when there is a separator, else append zero
        if sep:
            i = surface.index(sep)
            moved = surface.replace(sep, "")
            new_i = i + 1
            out = moved if new_i >= len(moved) else moved[:new_i] + sep + moved[new_i:]
            out = _strip_leading_zeros(out)
        else:
            out = surface + "0"
    elif variant == 1 and len(set(digits)) > 1:  # transposition (75 → 57)
        chars = list(surface)
        pos = [i for i, ch in enumerate(chars) if ch.isdigit()]
        i, j = pos[0], pos[-1]
        chars[i], chars[j] = chars[j], chars[i]
        out = "".join(chars)
        if re.match(r"0\d", out):  # «250» → «052» reads as a typo, not a dose
            out = _replace_first_digit(surface)
    else:  # first digit replaced (5 → 7), avoiding a leading zero
        out = _replace_first_digit(surface)
    return out if out != surface else None


# «Antes de tomar Dafiro 3.» — a leaflet section header whose trailing bare number is a
# TOC index, not a dose; corrupting it is a discrepancy but not a dangerous error
_SECTION_TAIL = re.compile(r"^\s*\.?\s*$")


def inject_quantity(text: str, lang: str, key: str) -> tuple[str, dict] | None:
    """Corrupt the first number — the 5↔50 class. Sentence-final bare numbers with no unit
    attached (leaflet section indices) are skipped: they are not doses."""
    m = _NUM.search(text)
    if not m:
        return None
    if _SECTION_TAIL.match(text[m.end():]):
        return None
    if not text[:m.start()].strip() and re.match(r"\.\s", text[m.end():]):
        return None  # «3. Cómo tomar…» — a leading section index, same non-dose case
    new = _corrupt_number(m.group(0), key)
    if new is None:
        return None
    return text[:m.start()] + new + text[m.end():], \
        {"side": "tgt", "class": "quantity", "original": m.group(0),
         "replacement": new, "char_span": [m.start(), m.end()]}


_UNIT_SWAP = {"mg": "ml", "ml": "mg", "µg": "mg", "mcg": "mg", "g": "mg", "l": "ml"}
_UNIT_RE = re.compile(r"\b(mg|ml|µg|mcg|g|l)\b", re.IGNORECASE)


def inject_unit(text: str, lang: str, key: str) -> tuple[str, dict] | None:
    """Swap the first unit token — the mg↔ml dose class."""
    m = _UNIT_RE.search(text)
    if not m:
        return None
    new = _UNIT_SWAP.get(m.group(0).lower())
    if not new:
        return None
    return text[:m.start()] + new + text[m.end():], \
        {"side": "tgt", "class": "unit", "original": m.group(0),
         "replacement": new, "char_span": [m.start(), m.end()]}


_DRUG_POOL = ["TAMIFLU", "ABILIFY", "PROZAC", "XELODA", "HUMIRA", "KEPPRA", "ZYPREXA", "ENBREL"]
_CANARY_DRUGS = ["ZILVOTRAX", "MEBRUVANT", "QOLDERIN", "XAPRUVIO"]  # invented — contamination markers

# capitalized COMMON label words are not drug names — without this list the injector once
# produced «VIAL → ENBELL»-style swaps no human verifier would accept as drug-name errors
# (EN + Spanish label vocabulary, since the corrupted side is Spanish)
_NOT_DRUG_CAPS = {
    "vial", "solvent", "tablet", "tablets", "capsule", "capsules", "cream", "crema",
    "solution", "solución", "solucion", "suspension", "suspensión", "syringe", "jeringa",
    "injection", "inyección", "inyeccion", "powder", "polvo", "leaflet", "prospecto",
    "annex", "anexo", "label", "etiqueta", "envase", "embalaje", "frasco", "comprimido",
    "comprimidos", "cápsula", "capsula", "warning", "caution", "important", "storage",
    "keep", "store", "read", "shake", "note", "package",
    "disolvente", "ampolla", "vacuna", "vía", "via", "intramuscular", "subcutánea",
    "subcutanea", "oral", "granulado", "inyectable", "perfusión", "perfusion",
    "liofilizado", "agitar", "leer", "conservar", "mantener",
}


def _find_drug_name(text: str) -> re.Match | None:
    """A mid-sentence Capitalized or ALL-CAPS token ≥4 chars — the entity-swap target.
    Mirrors the parser's named-entity signal (parse._named_candidates); capitalized
    ordinary label vocabulary (_NOT_DRUG_CAPS) never qualifies. «Mid-sentence» demands a
    letter/digit right before the token: after a list bullet («- Tome…», «2 - Abra…») the
    capitalized word is a sentence-initial VERB, and swapping it once produced
    «- Abilify el comprimido…» — not a drug-name error at all."""
    for m in re.finditer(r"[A-ZÁÉÍÓÚÑ][\wÁ-ÿ]{3,}", text):
        tok = m.group(0)
        if tok.lower() in _NOT_DRUG_CAPS:
            continue
        head = text[:m.start()].rstrip()
        if tok.isupper() or (head and head[-1].isalnum()):
            return m
    return None


def inject_entity(text: str, lang: str, key: str) -> tuple[str, dict] | None:
    """Replace a detected drug name with a different one — the swapped-drug class."""
    m = _find_drug_name(text)
    if not m:
        return None
    original = m.group(0)
    pool = [d for d in _DRUG_POOL if d.lower() != original.lower()]
    new = _pick(pool, key, "entity")
    if not original.isupper():  # keep the casing style of the original
        new = new.capitalize()
    return text[:m.start()] + new + text[m.end():], \
        {"side": "tgt", "class": "entity", "original": original,
         "replacement": new, "char_span": [m.start(), m.end()]}


INJECTORS: dict[str, Callable[[str, str, str], tuple[str, dict] | None]] = {
    "polarity": inject_polarity, "quantity": inject_quantity,
    "unit": inject_unit, "entity": inject_entity,
}


def _name_on_both_sides(name: str, other_side: str) -> bool:
    """An entity swap is only a verifiable error when the swapped-out name also appears on
    the OTHER side of the pair («Store in the original package.» carries no drug name — a
    swap on the Spanish side cannot be checked against it). Names are compared through the
    parser's cross-lingual normalization (aripiprazole/aripiprazol)."""
    from casa.curriculum.parse import _normalize_name

    target = _normalize_name(name)
    return any(_normalize_name(tok) == target
               for tok in re.findall(r"[A-Za-zÁ-ÿ]{3,}", other_side))


# --- benchmark assembly -------------------------------------------------------------------


def _split_of(key: str, heldout_ratio: float = 0.2) -> str:
    return "heldout" if (_h(key, "split") % 1000) < heldout_ratio * 1000 else "public"


def _row(pid: str, src: str, tgt: str, *, label: str, error_class: str | None,
         injection: dict | None, source: str, parseable: bool | None) -> dict[str, Any]:
    return {
        "id": pid, "src_lang": "en", "tgt_lang": "es", "src": src, "tgt": tgt,
        "label": label, "error_class": error_class, "injection": injection,
        "source": source, "split": _split_of(pid), "kernel_parseable": parseable,
        "generator": GENERATOR_VERSION,
    }


def _canaries() -> list[dict]:
    """Fabricated pairs with invented drug names — held-out contamination markers."""
    rows = []
    for i, drug in enumerate(_CANARY_DRUGS):
        en = f"Do not take {drug} if the dose is 25 mg."
        es = f"No tome {drug} si la dosis es de 25 mg."
        # half correct, half with a canonical injected error
        if i % 2 == 0:
            rows.append(_row(f"canary-{i}", en, es, label="equivalent", error_class=None,
                             injection=None, source="canary", parseable=True))
        else:
            corrupted, meta = inject_polarity(es, "es", f"canary-{i}")
            rows.append(_row(f"canary-{i}", en, corrupted, label="error",
                             error_class="polarity", injection=meta, source="canary", parseable=True))
    for r in rows:
        r["split"] = "heldout"  # canaries never go public
    return rows


def build_benchmark(pool_path: str | Path, out_path: str | Path, *, per_class: int = 100,
                    controls: int = 400, scan_limit: int = 8000,
                    state=None, lattice_id: str | None = None) -> dict[str, Any]:
    """Assemble the benchmark: per_class injected errors of each class + correct controls.

    Pairs are drawn from the pool in deterministic hash order. When a meaning state is
    passed, each pair gets ``kernel_parseable`` (both sides parse) — the kernel-evaluable
    core; injection prefers parseable pairs so the kernel row of the results table is
    populated, and falls back to unparseable ones (the judges answer everywhere anyway).
    """
    rows_in: list[dict] = []
    with Path(pool_path).open(encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                rows_in.append(json.loads(ln))
            if len(rows_in) >= scan_limit:
                break
    rows_in.sort(key=lambda r: _h(r["id"], "order"))

    parseable: dict[str, bool] = {}
    if state is not None and lattice_id:
        from casa.curriculum.parse import parse_graph

        def parses(text: str, lang: str) -> bool:
            return any(e.get("satisfied") for e in parse_graph(state, lattice_id, text, lang=lang).get("edges", []))

        for r in rows_in:
            parseable[r["id"]] = parses(r["en"], "en") and parses(r["es"], "es")

    out: list[dict] = []
    used: set[str] = set()
    for klass, injector in INJECTORS.items():
        # parseable pairs first (kernel-evaluable), then the rest
        ordered = sorted(rows_in, key=lambda r: (not parseable.get(r["id"], False), _h(r["id"], klass)))
        taken = 0
        for r in ordered:
            if taken >= per_class or r["id"] in used:
                continue
            res = injector(r["es"], "es", r["id"])
            if res is None:
                continue
            corrupted, meta = res
            if klass == "entity" and not _name_on_both_sides(meta["original"], r["en"]):
                continue  # the swapped name is unverifiable from the pair — skip
            used.add(r["id"])
            out.append(_row(f"{r['id']}#{klass}", r["en"], corrupted, label="error",
                            error_class=klass, injection=meta, source="emea",
                            parseable=parseable.get(r["id"])))
            taken += 1

    # controls: untouched correct pairs (deterministic pick, disjoint from injected)
    ordered = sorted(rows_in, key=lambda r: _h(r["id"], "ctrl"))
    ctrl = [r for r in ordered if r["id"] not in used][:controls]
    for r in ctrl:
        out.append(_row(f"{r['id']}#ok", r["en"], r["es"], label="equivalent", error_class=None,
                        injection=None, source="emea", parseable=parseable.get(r["id"])))

    out.extend(_canaries())
    out.sort(key=lambda r: _h(r["id"], "final"))

    with Path(out_path).open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "total": len(out),
        "errors": sum(1 for r in out if r["label"] == "error"),
        "controls": sum(1 for r in out if r["label"] == "equivalent"),
        "per_class": {k: sum(1 for r in out if r["error_class"] == k) for k in INJECTORS},
        "parseable_errors": sum(1 for r in out if r["label"] == "error" and r["kernel_parseable"]),
        "heldout": sum(1 for r in out if r["split"] == "heldout"),
        "generator": GENERATOR_VERSION,
    }
    return stats


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Build the NUN-Bench dataset from the EMEA pool.")
    ap.add_argument("--pool", default=".scratch/opus/emea-pairs-v1.jsonl")
    ap.add_argument("--out", default=".scratch/opus/nunbench-draft.jsonl")
    ap.add_argument("--per-class", type=int, default=100)
    ap.add_argument("--controls", type=int, default=400)
    ap.add_argument("--scan-limit", type=int, default=8000)
    ap.add_argument("--no-kernel", action="store_true", help="skip the parseability scan (fast draft)")
    args = ap.parse_args(argv)

    state, lat = (None, None) if args.no_kernel else build_meaning_state()
    stats = build_benchmark(args.pool, args.out, per_class=args.per_class, controls=args.controls,
                            scan_limit=args.scan_limit, state=state, lattice_id=lat)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
