# Agent store catalog v0 — как не потеряться в продуктах

**Date:** 2026-05-30  
**Status:** accepted (design)  
**Parent:** [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md), [`memory-hierarchy-v0.md`](memory-hierarchy-v0.md)  
**Companion:** [`context-axis-v0.md`](context-axis-v0.md)

---

## Store — что это (одна фраза)

**Agent store** = упакованная **LTM + NCA** (+ опц. bundles), которую **profile** подключает к одному CASA-core на boot.

Это **не** язык, **не** продукт и **не** корпус. Корпус — только **источник ingest**; продукт — **profile + act**.

```text
  [CASA core]     один runtime (predict → critic → sleep)
       ↑ boot
  [Agent store]   ltm/ + nca/  — «картридж памяти»
       ↑ recipe
  [Profile]       какие картриджи + modalities + act
       ↑ ship
  [Product]       IDE T9, Orion, bukvar, …
```

---

## Оси каталогизации (обязательные поля)

Каждый store описываем **вектором**, имя папки — лишь ярлык.

| Ось | Код | Примеры | Зачем |
|-----|-----|---------|--------|
| **locale** | `ru` \| `en` \| `multi` | ru, en | Алфавит / L2 shard family |
| **tier** | `general` \| `tech` \| `literary` \| `listen` \| `dev` | general, literary (afan) | Роль словаря, не «весь язык» |
| **layer_pack** | `lex` \| `lex+entity` \| `lex+vk` \| `full` | lex+entity для BiT9 | Что в ltm кроме L2 |
| **corpus_id** | строка | `detcorpus-50k-cc0`, `afan-v1`, `en-folk-gutenberg` | Откуда headwords (аудит) |
| **lifecycle** | `lab` \| `staging` \| `prod` | prod | Можно ли в profile release |
| **supersedes** | store_id \| null | `sss-ru-lexicon-v0` → general v1 | Линия наследования |

**Правило:** один **locale + один tier** для prod-RU lexicon в runtime — не два store на один слот profile.

---

## Именование папок (v0)

Шаблон:

```text
sss-{locale}-{tier}[-{qualifier}]-v{N}
```

| Компонент | Пример |
|-----------|--------|
| locale | `ru`, `en` |
| tier | `general`, `tech`, `literary`, `folk` |
| qualifier | опционально `sharded`, `console` (избегать имён корпуса в prod!) |
| N | `v0`, `v1` |

**Плохо:** `sss-afan-v0` как prod-RU (корпус в имени).  
**Хорошо:** `sss-ru-literary-v0` (роль), `sss-afan-v0` остаётся **ingest ref only**.

### Матрица quad (целевая)

| store_id | locale | tier | corpus_id |
|----------|--------|------|-----------|
| `sss-en-general-v0` | en | general | en-folk / gutenberg |
| `sss-en-tech-v0` | en | tech | repo-scan |
| `sss-ru-general-v0` | ru | general | detcorpus-50k-cc0 |
| `sss-ru-tech-v0` | ru | tech | repo-scan |
| `sss-ru-literary-v0` | ru | literary | afanasyev-624 (будущее переименование sharded) |

---

## Реестр (канон)

Файл: **`lab/agent-stores/catalog.v0.json`** (roadmap) — машиночитаемый индекс. Корень данных: [`lab-data-root-v0.md`](lab-data-root-v0.md).

```json
{
  "schema_version": 1,
  "stores": [
    {
      "store_id": "sss-ru-general-v0",
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
{ "role": "ru_lexicon", "store_id": "sss-ru-general-v0" }
```

Роли profile (фиксированный словарь v0):

| role | Обычно store tier |
|------|-------------------|
| `ru_lexicon` | ru / general (+ literary merge опционально) |
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
3. В `catalog`: `corpus_id: "merged:detcorpus+afan+tech-seed"`
4. Literary/Afan — вклад в merged или отдельный tier store только для lab сравнения

Пересечение лемм → **усиление votes**, не второй store (см. `norm_word` + один `lang.word.*`).

---

## Продукты ↔ stores (шпаргалка)

| Product | Profile | Stores (roles) |
|---------|---------|----------------|
| BiT9 semantic v1 | `bilingual-t9-console-v0` | `ru_lexicon` + `en_lexicon` |
| BiT9 layout-parity | `bilingual-layout-parity-v0` (future) | + `vk_core`, segment prose/command |
| IDE code | `dev-ide-complete-v0` | `en_command`, `ru_tech`, … |
| Bukvar / listen | listen profile | RU + hippo tier, не lexicon quad |

Новый продукт = **новый profile** или новая строка в catalog, **не** новый SN.

---

## Checklist перед добавлением store

- [ ] Заполнены оси locale / tier / corpus_id
- [ ] Не дублирует prod-слот без `supersedes`
- [ ] `export_ltm_pack` + manifest
- [ ] NCA CUDA для всех trainable L2 shards
- [ ] Запись в catalog + INDEX.md
