# CASA: ревью курса von-neumann (RU → native) — v1

**Статус:** living review (2026-06-07)  
**Аудитор:** Cursor agent (сессия curriculum review)  
**Основание:** NorthStar, agent-notes pedagogy, структура призм, TECH-DEBT-INDEX, class audit  
**Связано:** [agent-existence-north-star.md](agent-existence-north-star.md), [CASA-native-writer-criteria-v1.md](CASA-native-writer-criteria-v1.md), [CASA-von-neumann-ru-class-audit-v1.md](CASA-von-neumann-ru-class-audit-v1.md), [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md), [TECH-DEBT-INDEX.md](TECH-DEBT-INDEX.md)

---

## Резюме

Кодовая инфраструктура курса **в хорошей форме** (type-0 tick pipeline, OOA&D ADR-0056–0058). **Главный долг — эпистемический:** curated green (CEFR C2, B11 6/6) **не переносится** на claim «native» без open-world probe и слоёв RU-α…RU-ε.

| Вопрос | Ответ |
|--------|-------|
| Где мы на шкале? | Castles §1–§2 закрыты; §3 — **curated**; native (RU-N) — **не достигнут** |
| Согласовано с NorthStar? | Да: no LLM hot path, field-realize, duck test |
| Главный риск | CEFR/B11 green → overclaim «носитель везде» |
| Главный пробел к native | RU-ε `agent.world.*` + `probe_nositel_open_ru` |

---

## 1. NorthStar — два полюса, одна программа

| Полюс | Документ | Критерий |
|-------|----------|----------|
| **Существование субъекта** | [agent-existence-north-star.md](agent-existence-north-star.md) | persistence, память, действие, самопочинка, инициатива, provenance |
| **Владение языком** | [CASA-native-writer-criteria-v1.md](CASA-native-writer-criteria-v1.md) | письменный RU как инструмент; не § учебника |

**Инвариант:** hot path = field-realize (`subject_articulation`, `phrase_compose`) — **без LLM**. Любой «временный LLM» ломает оба NorthStar.

**Действие:** явная перекрёстная ссылка existence ↔ native-writer (см. § Remediation ниже).

---

## 2. Педагогика (agent-notes) ↔ реализация

### Core stack (RU written v1)

Источник: `agent-notes/.../pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md`

| Источник | Роль в CASA | Статус |
|----------|-------------|--------|
| Castles §1→§3 | лента блоков 1→9d | §1–§2 ✅; §3 curated |
| Ehri OM + NRP | grapheme → whole-word | ✅ |
| Hoover–Gough SVR | D × C = RC | D ✅; C partial |
| Stalega 2024 | **deny PA-only** | в каноне ✅ |
| Hansford 2025 | structured literacy | rationale |

### Anti-patterns (не откатывать)

- PA-only / three-cueing в новых moment plans
- CEFR green → «nositel везде»
- LLM на hot path «пока не готов»
- Один monolithic probe «весь русский»
- B11 paste-gates вместо prop-compose при обучении

---

## 3. Карта фаз RU → RU-N

| Фаза | Педагогика | Gate | Статус | Замечание |
|------|------------|------|--------|-----------|
| Phase I (блок 1–5) | Castles §1–§2 | corpus + lexical | ✅ | — |
| **RU-α** (5α) | Galperin material→verbal | `probe_material_verbal_ru` | ✅ train 3/3 + held-out 2/2 | `ingest_material_verbal_class` |
| Phase II (6–9) | phrase + morph | phrase-agent-store | ✅ | continuous ОБО — RU-β |
| **9d B11** | Castles §3 / ADR-0053 | `probe_text_meaning_ru` | 🟡 6/6 curated | held-out v2 — genre |
| 9c morphemics | B5 | `probe_morphemics_ru` | ✅ | — |
| 10–11 ortho/punct | L3–L4 | ortho 4/4, punct 3/3 | ✅ lab | — |
| Block 12 dialog | ADR-0045 | CEFR + nositel subset | 🟡 C2 curated | C1+ `wired: false` |
| **5f intent** | ADR-0057 personal tracts | `probe_intent_personal_ru` | 🟡 lab only | → mastery_gate |
| **RU-β** | productive morph | `probe_morph_productive_ru` | ❌ planned | neologism criterion |
| **RU-ε** | world model ADR-0054 | `probe_world_link_ru` | ✅ held-out 2/2 | `ingest_world_link_class` + train plan |
| **RU-N** | open native | `probe_nositel_open_ru` | ❌ scaffold | 7/7 criteria |

---

## 4. Структура призм (post OOA&D)

```text
passage/ → semantic_read → tract/ (+ intent/) → dialogue_bind/ (+ wm/)
  → discourse/ → articulate
```

| Пакет | LOC (≈) | ADR | Замечание |
|-------|---------|-----|-----------|
| `tick/discourse/` | 1777 | 0056 | ✅ |
| `memory/wm/` | 1113 | 0055 | ✅ |
| `memory/intent/` | 638 | 0057 | ✅; педагогический gate отставал |
| `tick/passage/` | 684 | 0053 | ✅ |
| `tick/tract/` | 397 | 0052 | ✅ |
| `domain/dialogue_bind/` | — | 0058 | ✅ |

### Следующие кандидаты OOA&D (не блокируют native)

| Файл | LOC | Приоритет |
|------|-----|-----------|
| `memory/memory_prisms.py` | ~992 | P3 — высокий риск |
| `control/sn_cen_runtime.py` | ~680 | P3 |
| `memory/lexicon_shard.py` | ~729 | P3 |
| `memory/gen_math_palochki_class.py` | ~1146 | P3 — authoring/ingest mix |

---

## 5. Технический долг (релевантный курсу)

См. [TECH-DEBT-INDEX.md](TECH-DEBT-INDEX.md) § Curriculum / native path.

| Id | Задача | Приоритет |
|----|--------|-----------|
| **CUR-1** | `probe_nositel_open_ru` + open plan disjoint от ingest | **P0** |
| **CUR-2** | B11 held-out v2 (genre: narrative/instruction/argument) | **P0** |
| **CUR-3** | RU-ε: `compile_world_bundle.py` + `agent.world.*` на store | **P1** |
| **CUR-4** | `skill.tract.personal` ↔ `probe_intent_personal_ru` в mastery_gate | **P1** |
| **CUR-5** | Нумерация: teaching «Блок 11» = punct (B9); categories B11 = 9d | **P2** |
| **CUR-6** | CEFR doc: C1/C2 не «ожидаем red»; отделить curated vs open | **P2** |
| **CUR-7** | `skill.spell/punct` уже в PROBE_GATE — проверить promote path | **P2** |
| **CUR-8** | Literature micro-class (Band B) — `probe_literature_rc_ru` | **P2** |
| **CUR-9** | B4 lexicon facets stratified held-out | **P3** |
| **CUR-10** | `promote_frame_from_journal` (ADR-0053 v2) | **P3** |
| **CUR-11** | RU-α/RU-ε teacher ingest CLI (train plan; held-out только probe) | **done** |

Инфра (не curriculum, но NorthStar persistence): T02-1/2/3, E0–E8, MP-5 partial.

---

## 6. Remediation log (устранение)

| Id | Действие | Статус |
|----|----------|--------|
| CUR-1 | `nositel-open-plan-v1.json` + `probe_nositel_open_ru.py` | **wired 5/5 green**; `ru_n_claim_pass` ждёт RU-β/ε |
| CUR-2 | `text-meaning-held-out-v2.json` + `--held-out-v2` | **done** |
| CUR-3 | `compile_world_bundle.py` + `probe_world_link_ru` + seed bundle | **probe 2/2 green** (journal path) |
| CUR-4 | `PROBE_GATE_BY_SKILL` + Block 5f | **done** |
| CUR-5 | B9/B11 numbering | **done** |
| CUR-6 | CEFR curated vs RU-N | **done** |
| RU-β | `probe_morph_productive_ru` plan (wired:false) | **scaffold** |
| CUR-11 | `ingest_material_verbal_class` + `ingest_world_link_class` + train plans | **done** (von-neumann ingested; train probe без inline remember) |
| doc | cross-links + TECH-DEBT | **done** |

*Обновлять таблицу при закрытии пунктов.*

---

## 7. Рекомендуемый порядок работ (после этого ревью)

1. **P0:** green на RU-α held-out; прогон `probe_nositel_open_ru` (ожидаем red — baseline).
2. **P1:** RU-ε world authoring + `probe_world_link_ru`; intent в mastery streak.
3. **P2:** B11 v2 genre frames compile; literature 3–5 сценариев; CEFR doc sync.
4. **P3:** OOA&D memory_prisms; facet routing B4.

---

## 8. Ссылки (pedagogy MCP)

| Тема | Path (agent-notes) |
|------|-------------------|
| RU index | `worlds/pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md` |
| Castles | `kb-pedagogy-ru-castles-2018-evidence-v1.md` |
| SVR | `kb-pedagogy-ru-hoover-gough-1990-svr-evidence-v1.md` |
| F→O | `worlds/pedagogy-general/playbook-pedagogy-fundamentals-to-operational-v1.md` |
| Goals | `casa-goals-and-roadmap-v1.md` |

---

*Версия: v1.0 · 2026-06-07 · living document — обновлять §6 при закрытии CUR-*
