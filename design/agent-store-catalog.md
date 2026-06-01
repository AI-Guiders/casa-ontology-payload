# Agent store catalog v0 — как не потеряться в продуктах

**Date:** 2026-05-30  
**Status:** accepted (design)  
**Parent:** [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md), [`memory-hierarchy.md`](memory-hierarchy.md)  
**Companion:** [`context-axis.md`](context-axis.md)

---

## Store — что это (одна фраза)

**Agent store** = упакованная **структура памяти** (`ltm/` + `nca/`); опц. `bundles/` — только ingest-след, не runtime.

Это **не** язык, **не** продукт и **не** корпус. Корпус — только **источник ingest**; продукт — **profile + act**.

```text
  [CASA core]     один runtime (predict → critic → sleep)
       ↑ boot
  [Agent store]   ltm/ + nca/  — память агента (NCA те же файлы, не «в картридж»)
       ↑ ingest (one-time / accelerated childhood)
  [Ingest]        bundles / corpus → материализация в память
       ↑ recipe
  [Profile]       какие store + modalities + act
       ↑ ship
  [Product]       IDE T9, Orion, bukvar, …
```
---

## Оси каталогизации (обязательные поля)

Каждый store описываем **вектором**, имя папки — лишь ярлык.

| Ось | Код | Примеры | Зачем |
|-----|-----|---------|--------|
| **locale** | `ru` \| `en` \| `multi` | ru, en | Алфавит / L2 shard family |
| **tier** | `general` \| `archaic` \| `tech` \| `literary` \| `listen` \| `dev` | general (DetCorpus), archaic (Afan dialect) | Роль словаря, не «весь язык»; `literary` → archaic в v0 |
| **layer_pack** | `lex` \| `lex+entity` \| `lex+vk` \| `full` | lex+entity для BiT9 | Что в ltm кроме L2 |
| **corpus_id** | строка | `detcorpus-50k-cc0`, `afan-v1`, `en-folk-gutenberg` | Откуда headwords (аудит) |
| **lifecycle** | `lab` \| `staging` \| `prod` | prod | Можно ли в profile release |
| **supersedes** | store_id \| null | `lexicon-ru-archaic` → general v1 | Линия наследования |

**Правило:** один **locale + один tier** для prod-RU lexicon в runtime — не два store на один слот profile.

---

## Именование папок (v0)

Шаблон:

```text
lexicon-{locale}-{tier}[-{qualifier}]
```

| Компонент | Пример |
|-----------|--------|
| locale | `ru`, `en` |
| tier | `general`, `archaic`, `tech`, `folk` |
| qualifier | опционально `sharded`, `console` (избегать имён корпуса в prod!) |

**Плохо:** `ingest-ref-afan` как prod-RU (корпус в имени).  
**Хорошо:** `lexicon-ru-archaic` (роль), `ingest-ref-afan` остаётся **ingest ref only**.

### Матрица quad (целевая)

| store_id | locale | tier | corpus_id |
|----------|--------|------|-----------|
| `lexicon-en-general` | en | general | en-folk / gutenberg |
| `lexicon-en-tech` | en | tech | repo-scan |
| `lexicon-ru-general` | ru | general | detcorpus-50k-cc0 (modern prod) |
| `lexicon-ru-tech` | ru | tech | repo-scan |
| `lexicon-ru-archaic` | ru | archaic | afanasyev-sharded (lab, не prod T9) |

---

## Реестр (канон)

Файл: **`lab/agent-stores/catalog.json`** (roadmap) — машиночитаемый индекс. Корень данных: [`lab-data-root.md`](lab-data-root.md).

```json
{
  "schema_version": 1,
  "stores": [
    {
      "store_id": "lexicon-ru-general",
      "locale": "ru",
      "tier": "general",
      "corpus_id": "detcorpus-50k-cc0",
      "lifecycle": "lab",
      "profile_roles": ["ru_lexicon"],
      "notes": "Частотник; не Afan"
    }
  ]
}
```

`lab/agent-stores/INDEX.md` — человекочитаемая проекция каталога.

**Profile** ссылается только на `store_id` + **role**, не на путь корпуса:

```json
{ "role": "ru_lexicon", "store_id": "lexicon-ru-general" }
```

Роли profile (фиксированный словарь v0):

| role | Обычно store tier |
|------|-------------------|
| `ru_lexicon` | ru / **general** (modern); archaic — отдельный store, не merge в prod |
| `en_lexicon` | en / general |
| `en_command` | en / tech |
| `ru_tech` | ru / tech |
| `entity_hub` | bundle, не отдельный store |
| `vk_core` | `agent-core` read-only pack |

---

## Слияние корпусов без двух RU runtime

Если русский один, а корпусов несколько:

1. **Merge headwords** (union + `norm_word`) → один `headwords.merged.v1.txt`
2. **Один** `init` + **один** remigrate + **один** NCA train (CUDA)
3. В `catalog`: `corpus_id: "merged:detcorpus+tech-seed"` (без archaic по умолчанию)
4. Afan/archaic — **отдельный tier store**; см. [`ru-lexicon-modern-archaic.md`](ru-lexicon-modern-archaic.md)

Пересечение modern∩archaic лемм → при осознанном merge только **overlap** усиливает votes; **archaic-only** (напр. `абазвався`) в prod не попадает.

---

## Продукты ↔ stores (шпаргалка)

| Product | Profile | Stores (roles) |
|---------|---------|----------------|
| BiT9 semantic v1 | `bilingual-t9-console` | `ru_lexicon` + `en_lexicon` |
| BiT9 layout-parity | `bilingual-layout-parity` (future) | + `vk_core`, segment prose/command |
| IDE code | `dev-ide-complete` | `en_command`, `ru_tech`, … |
| Bukvar / listen | listen profile | RU + hippo tier, не lexicon quad; фазы 0–2 → [`infancy-corpus-phases.md`](infancy-corpus-phases.md) |

Новый продукт = **новый profile** или новая строка в catalog, **не** новый SN.

---

## Checklist перед добавлением store

- [ ] Заполнены оси locale / tier / corpus_id
- [ ] Не дублирует prod-слот без `supersedes`
- [ ] `export_ltm_pack` + manifest
- [ ] NCA CUDA для всех trainable L2 shards
- [ ] Запись в catalog + INDEX.md
