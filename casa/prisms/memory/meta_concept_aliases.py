"""Канон lang.meta.*; legacy → canon (миграция store, не второй маршрут)."""

from __future__ import annotations

# legacy id → canonical (убрать из store через tools/migrate_lex_concept_store.py)
LEX_CONCEPT_RENAMES: dict[str, str] = {
    "lang.word.capital_letter": "lang.meta.letterCase.upper",
    "lang.word.lowercase_letter": "lang.meta.letterCase.lower",
    "lang.word.zaglavnaya": "lang.meta.letterCase.upper",
    "lang.word.strochnaya": "lang.meta.letterCase.lower",
    "lang.word.zaglavnaya_bukva": "lang.meta.letterCase.upper",
    "lang.word.capital-zaglavnaya-bukva": "lang.meta.letterCase.upper",
    "lang.word.bukva_verhnego_registra": "lang.meta.letterCase.upper",
    "lang.word.strochnaya_bukva": "lang.meta.letterCase.lower",
    "lang.word.bukva_nizhnego_registra": "lang.meta.letterCase.lower",
    "lang.word.bukva": "lang.meta.lexicon.grapheme",
    "lang.word.slovo": "lang.meta.lexicon.word",
    "lang.word.large": "lang.meta.size.large",
    "lang.word.small": "lang.meta.size.small",
    "lang.word.bolshaya": "lang.meta.size.large",
    "lang.word.malenkaya": "lang.meta.size.small",
    "lang.word.ne_znayu": "lang.meta.epistemic.unknown",
    "lang.word.vybor": "lang.meta.epistemic.choice",
    "lang.word.zameshatelstvo": "lang.meta.epistemic.confusion",
    "lang.word.glagol": "lang.meta.grammar.pos.verb",
    "lang.word.deystvie": "lang.meta.grammar.pos.action",
    "lang.word.sushchestvennoe": "lang.meta.grammar.pos.noun",
    "lang.word.apelsin_cap": "lang.word.apelsin",
    "lang.meta.size.comparative.greater": "lang.meta.compare.greater",
    "lang.meta.size.comparative.less": "lang.meta.compare.less",
}


def canonical_lex_concept_id(concept_id: str) -> str:
    cid = str(concept_id or "").strip()
    return LEX_CONCEPT_RENAMES.get(cid, cid)


def lex_concept_id_variants(concept_id: str) -> tuple[str, ...]:
    """После миграции store — один id; до миграции read path нормализует legacy в canon."""
    return (canonical_lex_concept_id(concept_id),)


def concept_lex_variants(concept_id: str) -> tuple[str, ...]:
    """Read-path variants including concept hub resolution (ADR-0073 P18b)."""
    try:
        from casa.prisms.memory.concept_layer import bind_concept_id, lex_for_locale

        hub = bind_concept_id(concept_id)
        variants = {canonical_lex_concept_id(concept_id), hub}
        for loc in ("ru", "en"):
            lex_id = lex_for_locale(hub, loc)
            if lex_id:
                variants.add(lex_id)
        return tuple(sorted(variants))
    except ImportError:
        return lex_concept_id_variants(concept_id)
