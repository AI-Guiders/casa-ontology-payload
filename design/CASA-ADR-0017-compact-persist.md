# CASA-ADR-0017: Compact persist (shipped memory flush, not tar)

**Статус:** принято (v0, 2026-06-01)  
**Область:** agent store / `ltm/` / multi-prism  
**Связано:** [`memory-hierarchy.md`](memory-hierarchy.md), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`ltm-pack.md`](ltm-pack.md)

---

## Контекст

Агент может **spawn** несколько content-призм (`prism_lang_ru`, `prism_math`, …). Runtime держит их в `field_state.json` (checkpoint). Компактная **долгая** память — `ltm/*.ltm` + `pack.manifest.json`.

v0 до ADR-0017: `export_ltm_pack` писал в основном `prism_memory`; spawn оставался только в checkpoint. Tar/profile pack — внешняя ops-упаковка, не решение агента.

---

## Решение

### 1. Compact persist — действие агента/субстрата

**API:** `casa.prisms.shared.compact_persist.compact_persist_store(store_dir, state, …)`

- Экспортирует **все** content-призмы (`list_content_prism_ids`), не только `prism_memory`.
- Пишет `ltm/` + обновляет `pack.manifest.json` (`prisms` registry, `prism_id` на каждой решётке).
- Опционально: `ltm/meta/router.json`, `ltm/meta/hot_context.jsonl` (audit).
- **Не** создаёт tar — дистрибутив снаружи.

### 2. Триггеры

| Триггер | Как |
|---------|-----|
| Явный | `compact_persist_store`, CLI `python -m casa.prisms.shared.compact_persist`, `prism_spawn --compact-persist` |
| После sleep | `store.compact_persist_on_sleep = True` или `LearningTickConfig.compact_persist_on_sleep` |
| Ops | `tools/export_ltm_pack.py` (как раньше; теперь default = все content prisms) |

### 3. Import

`import_pack` кладёт каждую решётку в призму по `prism_id` / `manifest.prisms` (обратная совместимость: без registry → `prism_memory`).

### 4. Что не входит

| Артефакт | Compact persist |
|----------|-----------------|
| `prism_agent`, `journal/` (Self) | нет без `agent_promote` |
| POST / integrity | host/KB, не ltm |
| `field_state.json` | отдельный runtime checkpoint |

---

## Root cause: `vocab too large` при миграции (не лечить skip)

| Симптом | `ValueError: vocab too large: 86624` в `export_ltm_pack` |
| Причина | Весь лексикон на **одной** решётке `L2_word` (legacy monolith), а не на `L2_word_00…63` |
| Почему ломается | `ltm_pack` v0: `vocab_n` — **u16** (≤65535); на monolith 86k+ уникальных токенов |
| Почему monolith | Ingest-ref / старые store до **corpus_quantile remigrate**; в docs был `tools/remigrate_l2_lex.py`, в репо не было |

**Исправление (canon):** `casa.prisms.memory.l2_remigrate` — вытащить headwords с monolith → `configure_lex_sharding` → `ingest_*_lex_batch` по шардам → очистить `L2_word`. Вызывается автоматически из `export_pack` / `migrate_thin_checkpoint` через `ensure_l2_sharded_for_export`.

CLI: `python tools/remigrate_l2_lex.py --store-dir … --write`

NCA на одной полке с 86k каналами по-прежнему невозможен — sharding это же требование [`l2-lattice-sharding.md`](l2-lattice-sharding.md).

### Шарды решёток ≠ несколько призм

При `vocab too large` и в UI/docs **не путать** два уровня (см. [`CASA-ADR-0016`](CASA-ADR-0016-prism-domains-hot-router.md)):

| Уровень | Что делим | Зачем | Пример id |
|---------|-----------|-------|-----------|
| **Решётка (shard)** | лексикон внутри **одной** content-призмы | u16 `.ltm`, NCA repair, равномерный vocab на полку | `L2_word_00` … `L2_word_63` |
| **Призма (prism)** | домен / stack / маршрут | RU vs math vs ingest, router, отдельный блок в `manifest.prisms` | `prism_lang_ru`, `prism_math` |

**Канон для переполненного monolith `L2_word`:** remigrate → **64 решётки** в той же призме (`prism_memory` или целевой `prism_lang_ru`), не «64 призмы с копией словаря».

- Виртуальный слой **`L2_word`** остаётся для babble/decode: merge legacy + все шарды ([`l2-lattice-sharding.md`](l2-lattice-sharding.md)).
- **Spawn второй content-призмы** не снимает лимит, если внутри неё снова один жирный `L2_word`.
- **Compact persist** пишет в `ltm/` **по решёткам** (каждый shard — свой `.ltm` + опц. `nca/L2_word_XX/`); в manifest — `prism_id` призмы-владельца, не отдельная призма на шард.

Порядок на lab store: `remigrate_l2_lex` (шарды) → `compact_persist` / thin checkpoint. Вынос RU в `prism_lang_ru` — отдельный шаг перекладки, **после** sharding.

---

## Thin runtime checkpoint (v0, 2026-06-01)

Проблема: `field_state.json` ~400 MiB дублирует `cells[]` (ADR-0002).

| Артефакт | Содержимое |
|----------|------------|
| `ltm/` | все content/control решётки (`.ltm`) |
| `field_state.json` с `"checkpoint_format": "thin_v1"` | hippo, hot, router, SN, meta — **без** cells |
| Resume | `boot_store(ltm)` + merge thin overlay |

При `save_runtime_state` и наличии `ltm/pack.manifest.json`: по умолчанию **thin** + `compact_persist_store` при dirty (sync ltm ← RAM).

Код: `casa.prisms.shared.runtime_checkpoint`, `store_persist.save_runtime_state(thin=…)`.

---

## Последствия

- Авономный агент может **сам** зафиксировать profile на диске компактно, без tar.
- Multi-prism store переживает cold boot из `ltm/` без обязательного полного JSON checkpoint.
- Runtime JSON — порядка MiB, не сотен MiB, когда есть shipped `ltm/`.

---

## Код

| Модуль | Роль |
|--------|------|
| `compact_persist.py` | `compact_persist_store`, `maybe_compact_persist_after_sleep` |
| `export_ltm_pack.py` | `iter_profile_lattice_exports`, manifest `prisms` |
| `import_ltm_pack.py` | `import_lattice_into_prism`, router meta |
| `memory_prisms.run_sleep` | опц. flush после sleep |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0017 + v0 implementation |
| 2026-06-01 | Секция «шарды ≠ призмы» (root cause / миграция) |
