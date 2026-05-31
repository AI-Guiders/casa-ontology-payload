# CASA-ADR-0007: agent profile и store-pack — один core, много продуктов

**Статус:** accepted (design + lab path)  
**Дата:** 2026-05-30  
**Область:** поставка агента, agent store, runtime boot, продуктовые профили  
**Связано:** [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`ltm-pack-v0.md`](ltm-pack-v0.md), [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md), [`multi-cylinder-memory-v0.md`](multi-cylinder-memory-v0.md), [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)  
**KB canon (deployment):** `ca-substrate-agent/kb-casa-deployment-tracks-v1.md` — **`Autonomous.Standalone`** · **`Autonomous.Integrated.CascadeIDE`** (не A/B); одна автономия, разные instance.

---

## Контекст

### Вопрос

Один и тот же CASA-core (SN/CEN/FPN, UC: predict → critic → sleep) может давать **разные продукты** — bilingual T9, IDE autocomplete, math schema — в зависимости от того, **какую память подключили** и **куда CEN шлёт act**?

**Да.** Это не новые «отделы мозга», а **сменные agent stores** + **profile manifest**.

### Что уже есть (lab v0)

| Кирпич | Где |
|--------|-----|
| **Store-pack unit** | `{store}/ltm/` + `{store}/nca/` — ADR-0002 |
| **Export / import** | `export_ltm_pack_v0.py`, `import_ltm_pack_v0.py` — см. [`ltm-pack-v0.md`](ltm-pack-v0.md) |
| **Boot** | `store_boot_v0.py`, `boot_linked_stores_v0.py` |
| **Modality router** | `unified_tick_v0.py` (script → T9 → ortho) |
| **Act (demo)** | `t9_runtime_v0.py`, `apps/Casa.T9.Console` |

**Не хватает:** формального **agent profile** (рецепт «какие stores + boot + act») и тонкой обёртки **`run_agent_profile_v0.py`**.

---

## Решение

### 1. Три слоя поставки (не смешивать)

```text
  [A] CORE RUNTIME          tools + predictor + UC loop (один репо / один wheel)
  [B] AGENT STORE(S)        {store}/ltm/ + {store}/nca/ (+ опц. bundles)
  [C] AGENT PROFILE         JSON: какие stores, boot, modalities, act
```

| Слой | Меняется между продуктами? | Пример |
|------|----------------------------|--------|
| **Core** | **нет** (версия runtime) | `casa-ontology-payload` tools |
| **Agent store** | **да** | `lab/agent-stores/sss-ru-lexicon-v0` |
| **Profile** | **да** | `bilingual-t9-console-v0.json` |

**Цилиндры** (`prism_memory`, `prism_hippo`, `prism_io`) и **SN/DMN/CEN** — **архитектура core**, не отдельный store «Dev-мозг».

### 2. Store-pack — канон export (не ручной tar)

**Поставка памяти** = каталог agent store после export:

```bash
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-en-folk-v0
# опционально: --compress  → .ltm.zst
```

Результат в store:

```text
{store}/
├── ltm/
│   ├── pack.manifest.json
│   └── **/*.ltm
├── nca/
│   └── **/model.pt          # опционально для T9-only demo
└── bundles/                 # опционально: hub, kb ingest
```

**Не включать в поставку (prod):**

- `field_state.json` (~400 MiB lab artifact)
- git history, checkpoints вне `nca/`
- сырой corpus (Afan txt, Gutenberg) — только **результат ingest** в `ltm/`

**tar.gz** — опциональная **транспортная обёртка** для release/CDN; канонический контракт — `ltm/` + `nca/` в store dir, собранные через `export_ltm_pack_v0.py`.

### 3. Agent profile v0 (рецепт продукта)

Файлы: `lab/agent-profiles/*.v0.json`

```json
{
  "schema_version": 1,
  "profile_id": "bilingual-t9-console-v0",
  "title": "Bilingual T9 (RU+EN) — console demo",
  "stores": [
    { "role": "ru", "store_dir": "lab/agent-stores/sss-ru-lexicon-v0" },
    { "role": "en", "store_dir": "lab/agent-stores/sss-en-folk-v0" }
  ],
  "boot": { "mode": "linked" },
  "export_before_ship": true,
  "modalities": ["script", "ambiguous_prefix", "t9"],
  "claims_nav_enabled": false,
  "act": {
    "kind": "stdio",
    "entry": "tools/t9_runtime_v0.py"
  }
}
```

| Поле | Смысл |
|------|--------|
| `stores[].store_dir` | путь к agent store (после export в нём есть `ltm/`) |
| `export_before_ship` | напоминание: перед release прогнать `export_ltm_pack_v0.py` |
| `boot.mode` | `single` \| `linked` |
| `modalities` | SN/router: что разрешено на hot path |
| `act` | куда уходит результат (stdio / MCP / IDE) — **продукт для пользователя** |
| `claims_nav_enabled` | **false** для UC-bench и demo «понял с поля» |

### 4. Runtime flow (сейчас + целевой)

**Сейчас (lab):**

```bash
python tools/export_ltm_pack_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0
python tools/boot_linked_stores_v0.py \
  --ru-store lab/agent-stores/sss-ru-lexicon-v0 \
  --en-store lab/agent-stores/sss-en-folk-v0
python tools/run_t9_demo_cycle_v0.py
python tools/store_boot_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --smoke
```

**Целевой:**

```text
  run_agent_profile_v0.py --profile bilingual-t9-console.v0.json
       │
       ├─► (optional) export_ltm_pack для каждого store
       ├─► boot_store / boot_linked_stores → runtime state
       ├─► SN: modalities from profile
       └─► act: spawn entry (Python stdio / C# exe / MCP bridge)
```

| Tool | Статус |
|------|--------|
| `export_ltm_pack_v0.py` | **есть** — канон export |
| `import_ltm_pack_v0.py` | **есть** — round-trip / merge |
| `store_boot_v0.py` | **есть** — boot из `ltm/` |
| `run_agent_profile_v0.py` | roadmap — обёртка над boot + act |

### 5. Продукт ≠ новый цилиндр

| Продукт | Store profile | Modality | Act |
|---------|---------------|----------|-----|
| **Bilingual T9 console** | RU + EN linked | script, T9 | `Casa.T9.Console` |
| **IDE autocomplete** | code-agent-lab | T9 / schema on symbols | MCP → editor |
| **Math L0 tutor** | F0 bundle store | schema | bench / future UI |
| **Language child (full)** | RU lexicon + listen mass tier | listen, surface, T9 | autonomous loop |

**Lazy lexicon** (MCP dictionary, web cold ingest) — **расширение store** на sleep, не отдельный продукт-core. См. work-note [`cursor-session-f4a4bba6-casa-lab-arc-v0.md`](../../../knowledge/work/cursor-session-f4a4bba6-casa-lab-arc-v0.md).

### 6. Tier поставки (наследие ADR-0002 + profile)

| Tier | Store содержит | Profile использует |
|------|----------------|-------------------|
| **A** | `ltm/` | T9, schema read |
| **A+** | `ltm/` + `nca/` | repair smoke, sleep finetune |
| **B** | + hub bundles | bilingual entity |
| **C** | episodic `etm/` (future) | персональный агент на device |

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Отдельный git repo на каждый продукт | дублирует core и UC |
| Один fat `field_state.json` в поставке | 400 MiB, ломает смысл ltm-pack |
| «Dev cylinder» в SN/DMN | домен = store/domain band, не новый organ |
| RAG tarball с markdown | против UC; KB = cold ingest, not hot act |
| Новый `pack_*.py` вместо export | `export_ltm_pack_v0.py` уже канон — не дублировать |

---

## Последствия

### Сразу можно (без нового кода)

- Export store через **`export_ltm_pack_v0.py`**
- Boot linked/single через существующие tools
- Комбинировать продукты сменой profile + store dirs

### Roadmap (lab)

- [ ] `run_agent_profile_v0.py` — thin wrapper
- [ ] CI: smoke profile после export ltm
- [ ] Публикация stores отдельно от core (GitHub releases; tar — опционально)

### Связь с public repo

Публичный preview = **core README + LICENSE + 1–2 profile + exported stores**, не обязательно full Afan. Orion / внешние ревьюверы — **profile manifest** как контракт продукта.

---

## Проверка

- [ ] Profile `bilingual-t9-console-v0` → `run_t9_demo_cycle_v0` green после export + linked boot
- [ ] Boot **только** из `ltm/` (+ optional `nca/`) без `field_state.json`
- [ ] Два profile на **одном** core runtime без пересборки Python

---

## Связанные документы

| Документ | Роль |
|----------|------|
| [`ltm-pack-v0.md`](ltm-pack-v0.md) | export/import команды |
| [`lab/agent-profiles/`](../lab/agent-profiles/) | profile JSON v0 |
| [`lab/agent-stores/INDEX.md`](../lab/agent-stores/INDEX.md) | store roles |
| [`CASA-ADR-0006`](CASA-ADR-0006-t9-predictive-text.md) | первый product modality |
| [`casa-glossary-v0.md`](casa-glossary-v0.md) § surface / predict / act |
