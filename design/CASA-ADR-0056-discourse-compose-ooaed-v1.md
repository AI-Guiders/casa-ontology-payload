# ADR-0056: Discourse Compose — OOA&D Package

**Status:** accepted  
**Date:** 2026-06-07  
**Related:** ADR-0055 (WM Prism), ADR-0053 (meaning graph), subject articulation tick

## Context

`phrase_compose.py` вырос до ~950 строк: budget, eligibility, block→clause, intent routing, WM, rewrite — всё в одном модуле. Длина ответа должна emergent из bind, а не из cue-shortcut. Нужна архитектура, куда добавлять новые block families и intent без правок монолита.

## Decision

Пакет `casa/prisms/tick/discourse/` — OOA&D слой:

```
discourse/
  model.py          — ClauseSketch, DiscourseSketch, DiscourseContext
  budget.py         — DiscourseBudget (score floor from bind)
  render.py         — sketch → surface text
  slots.py          — BlockSlots (frame → clause slots)
  policy.py         — BlockDiscoursePolicy (eligibility per intent)
  realizers/
    base.py         — BlockRealizer protocol, BlockRealizerRegistry
    blocks.py       — Dialog, Prop, Passage, Grammar, Journal, Lexeme, Morph
  wm.py             — WmBlockRealizer (ADR-0055)
  sketch.py         — DiscourseSketchBuilder
  strategies.py     — IntentStrategy per query_intent
  composer.py       — SubjectDiscourseComposer (orchestrator)
  rewrite.py        — register-shift rewrite helpers
  paste.py          — paste_ratio_against_blocks (probes)
```

### Patterns

| Pattern | Where | Role |
|---------|-------|------|
| **Value object** | `ClauseSketch`, `DiscourseSketch`, `DiscourseBudget` | immutable-ish sketches, no IO |
| **Context** | `DiscourseContext.bind(...)` | query + blocks + intent + emergent budget |
| **Strategy** | `BlockRealizer`, `IntentStrategy` | one family / one intent |
| **Registry** | `BlockRealizerRegistry` | ordered dispatch by `matches()` |
| **Facade** | `SubjectDiscourseComposer`, `phrase_compose.py` | tick entry, legacy imports |

### Length policy (unchanged semantics)

- Stop adding clauses when block score &lt; `DiscourseBudget.score_floor`.
- Brief partner turn → короткий greeting/thanks (`_BRIEF_DIALOG_PREFIXES`).
- Narrative self (`ru.dialog.self` …) — полный slot bind, не режется brief.
- WM — 1–2 clauses via `WmBlockRealizer`, second only when bind + intent support elaboration.

### Legacy facades

- `phrase_compose.py` — thin: `compose_subject_phrase` → `default_composer()`
- `discourse_core.py`, `wm_discourse.py` — re-export для старых import paths

## Adding a new block family

1. Class `FooBlockRealizer` in `realizers/blocks.py` (or new file): `matches()`, `realize(block, ctx)`.
2. Register in `default_block_realizer_registry()` **before** fall-through realizers.
3. Extend `BlockDiscoursePolicy.eligible()` if intent gating needed.
4. Tests in `tests/test_*_discourse.py`.

## Adding a new query intent

1. `class FooIntentStrategy` in `strategies.py`.
2. Register in `default_intent_strategies()`.
3. Wire probe / `classify_query_intent` upstream if new intent name.

## Consequences

- `phrase_compose.py` ~80 lines (facade only).
- WM, dialog, passage isolated — проще review и HCI search по классам.
- Новые призмы (world model, WM variants) — новый `BlockRealizer`, не правка compose loop.
