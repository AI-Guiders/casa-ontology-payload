# Карта миграции curriculum id-схемы (от Диминой стороны)

**Status:** scratch — координация перед кодом
**Date:** 2026-06-24
**Audience:** Света + оператор + Дима
**В ответ на:** [CASA-scratch-dima-concept-zone-handoff-v1.md](CASA-scratch-dima-concept-zone-handoff-v1.md)
**Normative:** [ADR-0085](CASA-ADR-0085-concept-zone-built-in-vs-earned-theories.md), [ADR-0083](CASA-ADR-0083-curriculum-ontology-agent-store.md), [ADR-0073](CASA-ADR-0073-concept-layer-lexicalization.md)

---

## Зачем этот док

Handoff просит согласовать схему id и порядок merge. Этот док — **реальный скоуп миграции
в curriculum-коде**, измеренный по факту (а не по плану до нашей сессии). Curriculum за
последнюю неделю **сильно вырос**: полный софт-домен, отрицание, числа, единицы, **валидатор
смысла** + reality-check (см. [ВАЛИДАТОР-СМЫСЛА-статус-и-план.md](ВАЛИДАТОР-СМЫСЛА-статус-и-план.md)).
Объём id-миграции теперь больше, чем в §«Планируемый slice». Предлагаемый шов:
**наши новые curriculum-части мигрируем мы; store-архитектуру — вы.**

## Шов (кто что делает)

| Часть | Кто | Почему |
|-------|-----|--------|
| `_concept_id`, хардкоды `lex.*`, names-рёбра, **наши тесты** | **Дима/агент** | писали на этой неделе; формат edge-ключей валидатора, отпечаток, классификатор знаем наизусть |
| `schema-math` → curriculum-решётка (только curriculum) | Дима/агент | знаем все точки; математику не трогаем |
| Built-In регистрация, `agent-concept-graph` @ `prism_agent`, catalog/`theories[]`, supersede-ceremony, `ensure_concept_built_in`, `tools/teach_curriculum_ontology.py` | **Света/оператор** | ваш субстрат (store, write_gate, genetic) |

## Скоуп в коде (факты на 2026-06-24)

### 1. Hub id — генератор ОДИН
- `casa/curriculum/concept_net.py:100` — `_concept_id(en) → "lex.{en}"`. **Единственный источник** hub-id.
- `casa/curriculum/glossary.py:33` — уже параметризован: `concept_prefix: str = "lex."`.
- → меняем на `concept.{slug}`. Хардкоды-хабы в источнике (≈одна строка + 2 места):
  - `casa/curriculum/parse.py:209` — `"lex.you"` (неявный субъект императива)
  - `casa/curriculum/roundtrip.py:183` — `src == "lex.you"`
  - `casa/curriculum/demo_repl.py:203` — `f"lex.{word}"`
  - `casa/curriculum/analogy.py:32` — парсер edge-ключей (комментарий + логика над `lex.`)
  - `casa/curriculum/equivalence.py` — разбор edge-ключей валидатора (`¬rel(lex.file×2)`)

### 2. RU/EN словарная единица → `lemma.{ru,en}.*`
- Сейчас curriculum не делает `lex.ru/en` (это в `concept_layer.py`, P18 — ваше). Curriculum
  кладёт **names-рёбра**: `concept|names|lang.word.<surface>`.
- Read/write sites names-рёбер (формат `|names|lang.word.`):
  - `casa/curriculum/translate.py:19` — `_NAMES = "|names|lang.word."` (+ read в `_name_edges`, `translate_term`)
  - `casa/curriculum/parse.py:67` — `pre = "|names|lang.word."` (стем-резолв)
  - `casa/curriculum/concept_net.py:224` — `names_of` читает тот же префикс
  - запись — в `glossary.py` (teach)
- → новый формат `concept.*|names|lemma.{ru,en}.*` + surface в metadata. **Один префикс-константой**
  закрывает все 3 read-site + write.

### 3. `schema-math` — узко, математику НЕ трогать
**Менять (curriculum-решётка):**
- `casa/curriculum/world.py:16` — `LATTICE = "schema-math"`
- `casa/curriculum/demo_repl.py:72` — `LAT = "schema-math"`
- `casa/curriculum/glossary.py:31`, `casa/curriculum/teach.py:19` — дефолт/конфиг

**НЕ трогать (легитимная математика):** `f0_math_ingest`, `memory_prisms`, `init_math_l0_lab`,
`bench_math_schema`, `f0_*_extract`, `predictor`, `bridge_math`, и их тесты (`test_f0_*`,
`test_vis_math_bridge`, …). Это math L0 @ `prism_math` — корректно.

> **Опция (ADR-0083 §5):** lab-harness (`world.py`/`demo_repl`) может остаться **эфемерным**
> с явной пометкой «lab-only», а не моделью store. Тогда для демо/валидатора достаточно
> (1) переименовать id-схему и (2) пометить решётку lab-only — без полной заливки на store.

### 4. Тесты (основная масса) — наши
`lex.*`-ассерты (исключая `test_concept_layer.py` — он ваш, P18):
`test_parse(8)`, `test_concept_net_base(6)`, `test_software_domain(5)`, `test_attributes(5)`,
`test_analogy(4)`, `test_quantity(3)`, `test_concept_net(2)`, `test_world/concept_net_wide/concept_index(по 1)`.
Плюс `schema-math` в наших curriculum-тестах (`test_roundtrip`, `test_situation*`, `test_negation`,
`test_equivalence`, …). ≈40 ассертов в ~12 файлах — механически, но писали мы.

## Предлагаемый порядок
1. **Централизовать шов** (поведение не меняется, тесты зелёные): `CONCEPT_PREFIX`,
   `CURRICULUM_LATTICE`, `NAMES_PREFIX` константами со старыми значениями.
2. **Флип** значений на `concept.`/`agent-concept-graph`/`lemma.` — однострочно.
3. **Починить ассерты** (`lex.apple` → `concept.apple`, edge-строки, отпечаток).
4. Категории JSON (`food`, `physical_object`, `on|arg1|…`) — **не трогаем** (как в handoff §6).

## Что НЕ в нашем скоупе
Store-регистрация Built-In, `agent-concept-core` index, `theories[]`/catalog rows,
`supersede_concept_theory`, mass `lang.word.*` lexicon migration, wide-net на store — **ваше**.
