# CASA-ADR-0043: Discourse read — canonical prose / KB

**Статус:** diagnostic only (superseded by [CASA-ADR-0044](CASA-ADR-0044-field-native-semantic-articulate.md) для primary path)  
**Репозиторий:** [casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload)  
**Связано:** ADR-0030 (L4 J0), ADR-0032 (R1 ≠ semantics), ADR-0033 (S-layer), ADR-0041 (journal witdb deferred), **ADR-0044** (field-native semantic articulate)

---

## Решение (одной фразой)

**Spike и bench** для честного gap-report: prose/KB retrieval vs literacy store. **Primary roadmap — ADR-0044** (semantic bind + articulate на поле); KB ingest — deferred transport, не шаг 2 обязательный.

---

## Spike (von-neumann, 2026-06)

Инструмент: `lab/visual-curriculum/bench_read_discourse_spike.py`  
Queries: `data/queries_canon_read_spike-v1.jsonl`

| Канал | Когда | Что меряет |
|-------|--------|------------|
| `sn_cen` | KB bundle в field | answer_blocks по query (J0 path) |
| `predict_t9` | всегда | vis/field hypothesis — **не** prose semantics |
| `phrase_event` | literacy store | match pilot phrase-events — **структура**, не определение |

**Ожидание на literacy-only store:** `read_at_1` низкий на canon queries; `gap=needs_kb_ingest` для определений; phrase_event hit только на pilot фразах (мама/мыла).

---

## Слои (target)

```text
W/E (literacy)     →  слова, слоты, events
S (discourse)      →  определение → claims / intent
J0 read            →  read@paraphrase ≥ 0.85
J0 write           →  articulation_realize + phrase fallback
```

---

## Implementation ladder

| # | Задача | Репо |
|---|--------|------|
| 1 | Spike bench + honest gap report | casa ✅ |
| 2+ | **→ см. ADR-0044** (semantic router, stance, hot path) | casa |

~~KB-first ladder удалён — не primary path.~~

---

## Non-goals

- Не учить «определение» через vis×lex sleep одной карточкой.
- Не подменять miss случайным claim (articulation no_memory).
- WitDB journal migration — ADR-0041, после native SQL.

---

## Acceptance

- Canon spike: после KB ingest `read_at_1 ≥ 0.5` на 6-query pilot; до ingest — отчёт с явным `needs_kb_ingest`.
- Literacy regressions: morph-agreement track остаётся green.
