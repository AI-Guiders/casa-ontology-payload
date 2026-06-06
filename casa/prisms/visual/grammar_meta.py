"""L2/L3 grammar meta checks — person, agreement, case (ADR-0030)."""

from __future__ import annotations

import importlib.util
import unicodedata
from pathlib import Path
from typing import Any

_META_CONCEPTS = (
    Path(__file__).resolve().parents[3]
    / "lessons"
    / "literacy-cards"
    / "tools"
    / "meta_concepts.py"
)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def _load_meta_module() -> Any:
    path = _META_CONCEPTS
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("casa_grammar_meta_concepts", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _meta_cards(attr: str) -> list[tuple[str, str, str]]:
    mod = _load_meta_module()
    if mod is None:
        return []
    raw = getattr(mod, attr, ()) or ()
    out: list[tuple[str, str, str]] = []
    for row in raw:
        if isinstance(row, dict):
            slug = str(row.get("frame_id") or row.get("slug") or "").removeprefix("grammar-").removeprefix("word-")
            out.append((slug, str(row.get("surface") or ""), str(row.get("concept_id") or "")))
        else:
            slug, surface, cid = row
            out.append((str(slug), str(surface), str(cid)))
    return out


def person_cards() -> list[dict[str, str]]:
    return [
        {"slug": slug, "surface": surface, "concept_id": cid, "frame_id": f"word-{slug}-sans"}
        for slug, surface, cid in _meta_cards("GRAMMAR_PERSON_CARDS")
    ]


def agreement_pairs() -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for _slug, surface, cid in _meta_cards("GRAMMAR_AGREEMENT_PHRASE_CARDS"):
        parts = _nfc(surface).split()
        if len(parts) < 2:
            continue
        agent, verb = parts[0], parts[1]
        groups.setdefault(cid, []).append({"agent": agent, "verb": verb})
    return [{"concept_id": cid, "pairs": tuple(pairs)} for cid, pairs in groups.items()]


def case_cards() -> list[dict[str, str]]:
    return [
        {"slug": slug, "surface": surface, "concept_id": cid, "frame_id": f"word-{slug}-sans"}
        for slug, surface, cid in _meta_cards("GRAMMAR_CASE_CARDS")
    ]


def person_concept_for_surface(surface: str) -> str | None:
    key = _nfc(surface).lower()
    for row in person_cards():
        if _nfc(str(row.get("surface") or "")).lower() == key:
            return str(row.get("concept_id") or "")
    return None


def case_concept_for_surface(surface: str) -> str | None:
    key = _nfc(surface).lower()
    for row in case_cards():
        if _nfc(str(row.get("surface") or "")).lower() == key:
            return str(row.get("concept_id") or "")
    return None


def agreement_concept_for_pair(agent: str, verb: str) -> str | None:
    a = _nfc(agent).lower()
    v = _nfc(verb).lower()
    for group in agreement_pairs():
        cid = str(group.get("concept_id") or "")
        for pair in group.get("pairs") or ():
            if _nfc(str(pair.get("agent") or "")).lower() == a and _nfc(str(pair.get("verb") or "")).lower() == v:
                return cid
    return None


def check_person_registry() -> dict[str, Any]:
    cards = person_cards()
    surfaces = {_nfc(str(c.get("surface") or "")).lower() for c in cards}
    concept_ids = {str(c.get("concept_id") or "") for c in cards}
    return {
        "ok": len(cards) >= 7 and len(surfaces) == len(cards) and len(concept_ids) == len(cards),
        "count": len(cards),
        "cards": cards,
    }


def check_agreement_registry() -> dict[str, Any]:
    groups = agreement_pairs()
    ok = bool(groups) and all(str(g.get("concept_id") or "") and g.get("pairs") for g in groups)
    return {"ok": ok, "count": len(groups), "groups": groups}


def check_case_registry() -> dict[str, Any]:
    cards = case_cards()
    ids = {str(c.get("concept_id") or "") for c in cards}
    want = {"lang.meta.grammar.case.nom", "lang.meta.grammar.case.acc"}
    return {"ok": want.issubset(ids), "count": len(cards), "cards": cards}


def quiz_person_surface(surface: str, *, hint: str | None = None) -> dict[str, Any]:
    expected = person_concept_for_surface(surface)
    got = hint if hint is not None else expected
    if expected and got == expected:
        verdict = "know"
    elif hint is not None and expected and got != expected:
        verdict = "wrong"
    elif hint is not None and not expected:
        verdict = "wrong"
    elif expected:
        verdict = "know"
    else:
        verdict = "empty"
    return {"surface": surface, "expected": expected, "got": got, "verdict": verdict}


def quiz_agreement_pair(agent: str, verb: str, *, hint: str | None = None) -> dict[str, Any]:
    expected = agreement_concept_for_pair(agent, verb)
    got = hint if hint is not None else expected
    if expected and got == expected:
        verdict = "know"
    elif hint is not None and expected and got != expected:
        verdict = "wrong"
    elif hint is not None and not expected:
        verdict = "wrong"
    elif expected:
        verdict = "know"
    else:
        verdict = "empty"
    return {
        "agent": agent,
        "verb": verb,
        "expected": expected,
        "got": got,
        "verdict": verdict,
    }


def quiz_case_surface(surface: str, *, hint: str | None = None) -> dict[str, Any]:
    expected = case_concept_for_surface(surface)
    got = hint if hint is not None else expected
    if expected and got == expected:
        verdict = "know"
    elif hint is not None and expected and got != expected:
        verdict = "wrong"
    elif hint is not None and not expected:
        verdict = "wrong"
    elif expected:
        verdict = "know"
    else:
        verdict = "empty"
    return {"surface": surface, "expected": expected, "got": got, "verdict": verdict}


def grammar_meta_report(probe: str) -> dict[str, Any]:
    if probe == "meta-grammar-person":
        rows = [quiz_person_surface(str(c.get("surface") or "")) for c in person_cards()]
    elif probe == "meta-grammar-agreement":
        rows = []
        for group in agreement_pairs():
            for pair in group.get("pairs") or ():
                rows.append(
                    quiz_agreement_pair(str(pair.get("agent") or ""), str(pair.get("verb") or ""))
                )
    elif probe == "meta-grammar-case":
        rows = [quiz_case_surface(str(c.get("surface") or "")) for c in case_cards()]
    else:
        raise ValueError(f"unknown grammar meta probe: {probe}")

    know = sum(1 for r in rows if r.get("verdict") == "know")
    return {
        "probe": probe,
        "rows": rows,
        "total": len(rows),
        "know": know,
        "pass": know == len(rows) and bool(rows),
    }
