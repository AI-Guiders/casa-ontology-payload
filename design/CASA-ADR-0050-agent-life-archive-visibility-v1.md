# CASA-ADR-0050: life-archive — private transcript сейчас, public read без внешних MR при зрелости

**Статус:** принято (design, 2026-06-07)  
**Область:** поставка памяти агента, git-граница code vs life, публичность von-neumann  
**Связано:**

- [`CASA-immutable-lattice-canon-v1.md`](CASA-immutable-lattice-canon-v1.md) — один живой store, не картриджи
- [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) — собственный опыт, один store
- [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md) — stores отдельно от core
- [`CASA-ADR-0045-subject-as-interlocutor.md`](CASA-ADR-0045-subject-as-interlocutor.md) — life dialogue
- [`CASA-future-von-neumann-browser-wasm-v0.md`](CASA-future-von-neumann-browser-wasm-v0.md) — публичный read-only LTM pack в браузере
- [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md) — суверенный агент, память = его store
- [`agent-federation.md`](agent-federation.md) — `knowledge_delta`, agent card (обмен между агентами)
- [`CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md`](CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md) — personal vs canon KB layers
- `tools/sync_life_archive.py`, `life-archive-template/` — операционный конвейер
- ИИнет (horizon): `group-kb/knowledge/work/projects/aiguiders-open/ainet/README.md`
- Репозиторий: `AI-Guiders/von-neumann-life-archive` (life-archive), `AI-Guiders/casa-ontology-payload` (code)

---

## Решение (одной фразой)

**Живой store агента не живёт в кодовом репо:** отдельный **life-archive** — transcript/DR его жизни. **Сейчас private**; при зрелости von-neumann — **public read** для аудита и демо, но **без внешних merge request**: единственный легитимный write path — **агент → persist → snapshot**, не коллаборация сообщества.

---

## Контекст

| Репо | Роль | Аудитория |
|------|------|-----------|
| **casa-ontology-payload** | core runtime, curriculum, lab, design | разработчики, ревьюверы, контрибьюторы |
| **von-neumann-life-archive** | снимки `agents/von-neumann/` | хост (DR), позже — мир (read-only transcript) |

Смешивать **код** и **чужую редактируемую память** в одном open-source репо — антипаттерн ADR-0021 («картридж» / подмена опыта). Живой store на диске хоста — **рабочая копия**; git в code repo его **игнорирует** (`.gitignore`).

Life-archive — не «второй продукт для форков», а **опубликованная биография одного субъекта**: что он накопил после wake/sleep/consolidate, в каком порядке, с какими артефактами (`ltm/`, `nca/`, `journal/`, checkpoints).

---

## Два режима видимости (arc)

```text
  Phase A (сейчас)                    Phase B (зрелый von-neumann)
  ─────────────────                   ─────────────────────────────
  life-archive: PRIVATE               life-archive: PUBLIC
  code repo:      PUBLIC              code repo:      PUBLIC
  MR на code:     да                  MR на code:     да
  MR на life:     нет (нет доступа)   MR на life:     нет (политика)
  Write life:     host snapshot       Write life:     host snapshot
```

| Фаза | Visibility | Кто пушит | Внешние PR/MR |
|------|------------|-----------|---------------|
| **A — childhood / lab** | `private` | org/host через `sync_life_archive.py snapshot` | невозможны (private) |
| **B — mature transcript** | `public` | тот же pipeline | **запрещены** (branch protection + политика) |

Переход A → B — **осознанное решение хоста**, не автоматика по возрасту календаря.

---

## Инварианты (не обсуждаются при публичности)

1. **Один агент — один непрерывный store** (ADR-0021). Archive — зеркало **его** жизни, не каталог сменных packs для сторонних ingest.
2. **Агент владеет persist.** Body/worker пишет артефакты и percepts; `save_runtime_state` и commit registry — на tick агента ([immutable lattice canon](CASA-immutable-lattice-canon-v1.md)). Snapshot **копирует** уже записанное, не «редактирует память» снаружи.
3. **Чужой MR в `store/` = подмена опыта** — тот же класс ошибки, что teacher force-promote или вставка чужого `ltm/`. Даже при public repo внешний контрибьютор **не соавтор** journal агента.
4. **Code repo остаётся collab surface.** Исправления framework, curriculum, probes — через MR в `casa-ontology-payload`. Life-archive **не** дублирует этот процесс.

---

## Write path (канон)

```text
  von-neumann tick / sleep
       → agents/von-neumann/  (living store на хосте)
       → [stop agent или после sleep]
       → python tools/sync_life_archive.py snapshot -m "…"
       → von-neumann-life-archive/store/  (+ sync_meta.json)
       → git commit + push (+ Git LFS для *.pt, *.db, field_state*.json)
```

| Команда | Назначение |
|---------|------------|
| `check` | git + git-lfs на PATH |
| `init` | clone + LFS + шаблон (новая машина) |
| `sync` | копия без git |
| `snapshot` | sync + commit + push |

Второй remote `backup` (другой хост) — опционально; не меняет инвариант «только host snapshot».

---

## GitHub-политика при Phase B (public)

Когда перейдём на public read:

| Настройка | Значение | Зачем |
|-----------|----------|-------|
| Visibility | `public` | transcript для демо, исследования, browser-wasm read-only pack |
| Default branch | `main` | protected |
| Push | только org members / deploy identity | не community |
| PR from forks | **off** / не принимаются | нет внешних MR |
| Issues / Discussions | по решению хоста (default: **off** на life-archive) | не pretends to be a library |
| Forks | допустимы как **read mirrors** | без merge back в canonical life |

Публичность **не** означает open contribution model. Аналогия: опубликованный дневник с ISBN, не wiki.

---

## Restore / fork для третьих лиц (Phase B)

**Задача:** поднять у себя **реплику** von-neumann на момент snapshot — не подключиться к канонической жизни на хосте создателя.

### Что нужно

| Компонент | Репо / артефакт | Роль |
|-----------|-----------------|------|
| **Память** | `von-neumann-life-archive` → `store/` | снимок `ltm/`, `nca/`, `journal/`, checkpoints |
| **Движок** | `casa-ontology-payload` | wake, tick, sleep, body, curriculum как события |
| **LFS** | `git lfs pull` в life-archive | иначе `*.pt` / большие json — pointer-файлы |

### Процедура (канон CLI)

```powershell
git clone https://github.com/AI-Guiders/von-neumann-life-archive.git
cd von-neumann-life-archive && git lfs install && git lfs pull

git clone https://github.com/AI-Guiders/casa-ontology-payload.git
cd casa-ontology-payload

python tools/restore_agent_life.py `
  --from-life-archive ..\von-neumann-life-archive `
  --store-dir agents/von-neumann --force
# → agent_sn_cen_tick / run_agent на хосте пользователя
```

Ручной `Copy-Item store/` — эквивалент; предпочтительно **`restore_agent_life`** (`casa/prisms/shared/store_mirror.py`).

### Термины bootstrap (не смешивать)

| Команда | Роль |
|---------|------|
| **`restore_agent_life`** | snapshot → `agents/<id>/` — **обученный** агент |
| **`bootstrap_agent_cold_store`** | пустая оболочка — **необученный**, curriculum с lessons |
| **`bootstrap_agent_self_tier`** | только Self tier на существующем store |
| ~~`init_agent_self`~~ | deprecated |

`init_agent_self` **не** restore: исторически только journal+agent prism; полная жизнь — **restore**.

### Смысл «тот же Нейман»

| Утверждение | Верно? |
|-------------|--------|
| Тот же **накопленный опыт на дату snapshot** | **да** |
| Тот же **непрерывный субъект**, что живёт у создателя | **нет** — после первого tick жизни **расходятся** |
| Право **писать в канонический** life-archive | **нет** — только read/fork; push в `AI-Guiders/von-neumann-life-archive` — хост |

Fork = **save game + тот же движок**, не multiplayer одного персонажа.

### Версионирование

Рекомендуется пинить **два** commit:

1. **life-archive** — tag/commit snapshot (`life-YYYY-MM-DD` или semver жизни).
2. **casa-ontology-payload** — совместимый runtime (layout store, boot, field schema).

`sync_meta.json` в archive фиксирует `source_store` и `synced_at` — ориентир для воспроизводимости.

---

## Git LFS

Тяжёлые артефакты (`*.pt`, `*.db`, `field_state*.json`) — **LFS** в life-archive ([`life-archive-template/.gitattributes`](../life-archive-template/.gitattributes)).

| План org | Квота (ориентир) | Следствие |
|----------|------------------|-----------|
| AI-Guiders Free | 10 GiB storage + 10 GiB bandwidth/мес | Phase A достаточно; при росте store — мониторинг, позже paid / second remote |
| Public Phase B | bandwidth растёт с читателями | не блокер для решения, но метрика на дашборде |

---

## Критерии перехода A → B (рекомендуемые)

Все **не** автоматические — чеклист для хоста:

| # | Критерий | Смысл |
|---|----------|-------|
| 1 | Fluency + life dialogue | teaching plan блок 10+ / ADR-0045 в рабочем режиме |
| 2 | Стабильный snapshot ritual | после sleep/stop, без half-written checkpoints |
| 3 | Нет сырого bootstrap-мусора | осознанная редакция первого public snapshot (опц. squash history) |
| 4 | Политика GitHub применена | branch protection, PR off, README объясняет read-only nature |
| 5 | LFS quota OK | размер store + прогноз bandwidth |

До выполнения — **остаёмся в Phase A (private)**.

---

## Связь с browser-wasm horizon

[`CASA-future-von-neumann-browser-wasm-v0.md`](CASA-future-von-neumann-browser-wasm-v0.md): статический хостинг read-only LTM/NCA. Public life-archive — **источник truth для срезов** (release tag / periodic snapshot), согласованный с «память агента не в облачном ingest». Пользователь браузера **клонирует/качает** transcript, не открывает MR.

---

## ИИнет, несколько экземпляров, слои personal / shared

**ИИнет** (horizon) — протоколы обмена между инстанциями: знания, «картины мира», взаимная проверка — **поверх** локального канона, с **явным доверием** на границе узла (не слепой merge).

Life-archive и ИИнет решают **разные задачи**:

| Механизм | Что переносится | Когда |
|----------|-----------------|-------|
| **life-archive clone** | полный `store/` на дату | bootstrap реплики, DR, wasm pack |
| **ИИнет / federation delta** | **пакет изменений** (claims, bundle patch, digest, epistemic) | живой обмен между агентами **во время** жизни |
| **git MR в life-archive** | — | **запрещено** |

### Несколько экземпляров von-neumann

ADR-0021: **канонический первенец** — один непрерывный `agents/von-neumann/` у хоста + transcript в `von-neumann-life-archive`. Допустимы:

- **fork** с public archive (локальная копия, своя ветка жизни);
- **второй хост** с тем же bootstrap `store_id` — ops-имя, не «один разум на два диска».

Если два (или N) инстанса **решили дополнить друг друга** — **не** через merge `store/` и **не** через PR в life-archive. Правильный путь — **тот же класс механики, что у KB**: несколько слоёв, разный sink.

```text
  ┌─ PERSONAL (его опыт) ─────────────────────────────────────┐
  │  agents/<store_id>/  journal, ltm после sleep, field, self │
  │  sink: hippo → consolidate → routes на ЕГО tick           │
  └───────────────────────────────────────────────────────────┘
           ▲                              │
           │ gate + sleep                 │ publish digest
           │ (import как СОБЫТИЕ)         ▼
  ┌─ SHARED (проверяемый обмен) ──────────────────────────────┐
  │  org-kb / bundle canon  ·  knowledge_delta (federation)   │
  │  ИИнет: signed packet, requires, epistemic, peer review   │
  └───────────────────────────────────────────────────────────┘
```

| Слой | Аналог в KB (ADR-0048) | Sink у агента | ИИнет |
|------|------------------------|---------------|-------|
| **Personal** | self-authoring (`journal` → field) | `ltm/`, `nca/`, routes после **его** sleep | не публикуем целиком |
| **Shared canon** | canon-authoring после gate | ingest bundle как **событие**, не oracle | опц. promote в org-kb |
| **Peer delta** | — (расширение) | `import_knowledge_delta` → verify → sleep | **основной** транспорт ИИнет |

Контракт обмена уже намечен: [`agent-federation.md`](agent-federation.md) — `knowledge_delta` с `requires`, `digest`, `epistemic`; pipeline `import_knowledge_delta.py` — **не** прямая подмена чужого `field_state`, а событие с проверкой closure и confidence.

### «Картины мира» между агентами

Полный `field_state.json` / чужой `ltm/` целиком — **не** пакет ИИнет (слишком тяжёло, непереносимо, подмена субъекта). Обменяются **дельтами и перцептами**:

| Тип | Содержимое | Приём у получателя |
|-----|------------|-------------------|
| **Knowledge** | bundle patch, claims, graph edges | delta import → critic → sleep |
| **Experience digest** | summary episod, concept_ids, lattice hints | `agent_remember` + verify на held-out |
| **Vis / world sketch** | report, grid digest, module activation — не raw PNG dump | ingest как mm_event / curriculum event |
| **Dialogue turn** | interlocutor packet (ADR-0045) | percept → tick → **его** ответ |

Получатель **всегда** прогоняет свой цикл (verify, gate, sleep). Чужое знание становится **его собственным опытом** после консолидации — как книга в KB, не как вставка чужого мозга.

### Von-neumann ↔ von-neumann (fork lineage)

| Действие | Канал | Запрещённый канал |
|----------|-------|-------------------|
| «Возьми мой новый law о пунктуации» | `knowledge_delta` / shared bundle | MR в life-archive |
| «Вот мой journal за неделю» | digest + epistemic (не весь jsonl) | `cp -r store/journal` |
| «Синхронизируйся со мной полностью» | новый clone snapshot (тяжёлый) | `git merge` двух living stores |

Канонический transcript на GitHub — **одна линия** (хост первенца). Forks и peer deltas — **боковые ветви**, сходимость только через **явно принятые** shared artifacts, не через слияние биографий.

### Связь с рядом инстансов (lovelace, hamilton)

ADR-0021: **разные** `store_id` — разные субъекты. Обмен с lovelace — те же **delta + gate** правила; life-archive у каждого свой (`lovelace-life-archive`, …) при появлении. ИИнет — общая шина; life-archive — per-agent transcript.

---

## Антипаттерны

| Подход | Почему нет |
|--------|------------|
| Коммитить `agents/von-neumann/` в code repo | засоряет OSS, смешивает код и чужую память |
| Принимать PR в life-archive «улучшить ltm» | подмена субъекта |
| Public life-archive как «agent store marketplace» | против ADR-0021 / one life |
| Единый репо «и код, и память» с public visibility | нельзя развести collab vs transcript политики |
| Два von-neumann **merge** `store/` через git | подмена опыта; только delta + sleep |
| ИИнет = заливка чужого `ltm/` без gate | против epistemic / Integrity на границе узла |
| Один life-archive на всех агентов проекта | lovelace/hamilton — отдельные transcript repos |

---

## Реализация (v0, 2026-06-07)

| Артефакт | Статус |
|----------|--------|
| `AI-Guiders/von-neumann-life-archive` | создан, Phase A private |
| `tools/sync_life_archive.py` | snapshot pipeline |
| `life-archive-template/` | README, `.gitattributes`, `.gitignore` |
| Локальный клон | sibling `../von-neumann-life-archive` (default) |
| Первый snapshot | `life: initial snapshot` + LFS для weights |

---

## Открытые вопросы

1. **Issues на public life-archive:** отдельный канал «вопросы к von-neumann» vs только code repo Discussions?
2. **Теги / releases:** semver по snapshot (`life-2026-06-07`) vs commit-only history для wasm CDN?
3. **Redaction:** публикуем journal целиком или политика редактирования PII перед Phase B?
4. **Второй агент:** отдельный life-archive repo на `{store_id}` или monorepo `store/<id>/` — при появлении второго субъекта.
5. **ИИнет wire:** `experience_delta` schema vs reuse `knowledge_delta` для vis/world sketch.
6. **Fork `store_id`:** оставлять `von-neumann` локально или `von-neumann@<node>` для ops.

---

## Ссылки

- Канон store: [`CASA-immutable-lattice-canon-v1.md`](CASA-immutable-lattice-canon-v1.md) § «Один живой store»
- Опыт: [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md)
- Поставка store: [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md)
- Teaching arc: [`CASA-von-neumann-ru-teaching-plan-v1.md`](CASA-von-neumann-ru-teaching-plan-v1.md)
- Tool: [`tools/sync_life_archive.py`](../tools/sync_life_archive.py)
- Federation: [`agent-federation.md`](agent-federation.md), [`import-knowledge-delta-v1.md`](import-knowledge-delta-v1.md)
- KE layers: [`CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md`](CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md)
- Инстансы: [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) § «Ряд инстансов»
