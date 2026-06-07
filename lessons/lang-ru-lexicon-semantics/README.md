# RU lexicon semantics (Block 11 / ADR-0053)

Transport for `kb-lang-ru-lexicon-semantics-v1.bundle.json`.

Frames for meaning graph: `ru.prop.*` event, inference, stance, register.

Hot path: `passage_meaning.py` reads `meaning_frame` / `meaning_emit` claims from this bundle
(generic matcher). New speech situation → new claim here, not Python if-ladder (ADR-0053).

Canonical JSON: `agents/von-neumann/bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json`

Class: `lessons/ru-text-comprehend/` — probe `probe_text_meaning_ru`
