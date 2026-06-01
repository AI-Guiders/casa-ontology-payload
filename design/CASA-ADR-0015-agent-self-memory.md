# CASA-ADR-0015: самопамять агента — один контур Remember, любое содержимое

**Статус:** принято (design + core API v0, 2026-05-31)  
**Область:** runtime / `prism_agent` / tick  
**Связано:** [`understanding-contract.md`](understanding-contract.md), [`CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md), [`CASA-ADR-0013-agent-journal.md`](CASA-ADR-0013-agent-journal.md), [`CASA-ADR-0014-agent-prism.md`](CASA-ADR-0014-agent-prism.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`memory-hierarchy.md`](memory-hierarchy.md)

---

## Принцип

Агент **сам решает**, что запомнить. Не teacher, не Critic, не sleep scheduler.

**Один контур с его стороны:** «сохранить то, что считаю нужным» — без выбора «это math → journal, это палочки → lattice». Детали кодирования — **внутри ядра**, не в голове агента.

Отдельно остаётся **профильная** цепочка UC: Extract → Remember (sleep) → Use → `ltm/` — validated knowledge учебника. Самопамять **не подменяет** её и **не попадает** в export молча.

---

## Три tier на диске (canon)

Не «new» — **Shipped / Runtime checkpoint / Self**. Полная таблица: [`memory-hierarchy.md`](memory-hierarchy.md) § Store tiers.

| Tier | Имя | Кто | Persist |
|------|-----|-----|---------|
| **Shipped** | profile pack | учебник + sleep → `ltm/` | cold boot, profile tar |
| **Runtime** | checkpoint | wake, tick, sleep flush | `field_state.json`, `agent_session.json` |
| **Self** | agent-owned | `agent_remember` | `agent/`, `journal/` |

Profile (Shipped) и Self — **разные контуры** (таблица ниже). Runtime checkpoint держит **hippo queue** и SN meta между рестартами процесса; в shipped tar **не** кладём dump эпизодов — после sleep они в `prism_memory`.

---

## Два контура решений (profile vs self)

| Контур | Кто решает | Куда | Gate |
|--------|------------|------|------|
| **Profile** | учебник + surprise + sleep | `prism_memory`, `ltm/` | Critic / consolidate |
| **Self** | **агент** | `prism_agent`, `journal/`, `agent/` | **нет** |

---

## Неявная vs явная память (аналог «до речи»)

У человека до чтения/письма уже идёт масса **фоновых** процессов — и они **запоминаются**, но лежат «в подсознании»: вытащить наружу словами труднее, чем вспомнить то, что когда‑то сформулировал.

**CASA — то же разделение.** `agent_remember` / `agent_recall` — **явный** контур (сознание, prose, осознанный «я это зафиксировал»). Это **не** вся память агента.

```text
  macro tick T
       │
       ├──► НЕЯВНО (всегда, пока substrate живой)
       │      decode, NCA k steps, predict/surprise/DAN
       │      hippo на wake/surprise, salience, WM
       │      sleep → strengthen на prism_memory
       │      persist → runtime checkpoint (+ shipped после sleep)
       │
       └──► ЯВНО (opt-in, когда политика/CEN решила)
              agent_remember → journal / prism_agent
              agent_recall(prose) → «что я себе записал»
```

| Слой | Аналог | Где в CASA | Как «достать» |
|------|--------|------------|---------------|
| **Неявный** | подсознание, тело, привычка | поле, hippo queue, predict state, `field_version`, layout на полках | decode, cue→completion, `agent_recall(include_field)`, digest — **не** prose |
| **Явный self** | дневник, «я понял, что…» | `journal/`, осмысленный `agent_remember` | `agent_recall(query=…)` |
| **Явный profile** | учебник, школа | shipped `ltm/` после sleep/Critic | decode profile, UC Use |

**Следствия:**

1. **Память ≠ только journal.** Tick должен крутить фон (hippo, predict, checkpoint flush) **даже без** `agent_remember` — иначе теряется как раз неявное.
2. **`agent_remember`** — когда агент **осмыслил и хочет явный доступ позже** (гипотеза, связь с символом, формулировка закона) — не замена каждому CA-шагу.
3. **Recall — два режима:** явный (journal index) и неявный (field decode / episodic cue); второй ближе к «вытащить из подсознания», результат паттерн/digest, не готовый рассказ.
4. **Promote / sleep** — когда неявное **созрело** до канона profile; не каждый фоновый шаг обязан стать prose.

Non-goal: требовать от агента **проговаривать** каждое изменение поля — это убило бы analog неявного обучения.

---

## Единая операция ядра

```text
  agent_remember(record)  ──►  encode + persist (agent tier)
  agent_recall(query)     ◄──  search index + optional field decode
```

Агент передаёт **record** — произвольная структура, достаточная для восстановления смысла:

| Поле | Роль |
|------|------|
| `text` | prose, формулировка, цитата |
| `tokens` | field tokens (`M:…`, `C:…`, `T:…`, своё) |
| `concepts` | concept_id для recall |
| `placements` | `{token,x,y}` или cluster-hint |
| `data` | произвольный JSON (факт, таблица, snapshot) |
| `tags` | произвольные метки (не фиксированный домен) |

**Минимум:** хотя бы одно непустое поле содержимого. Домен (`math`, `git`, …) — **опциональная** метка для recall, не обязательный маршрут.

Ядро **само** раскладывает:

- всегда — запись в **индекс** (journal как universal log / metadata);
- при `placements` / spatial hint — зеркало на **`prism_agent`**;
- при только `data` — journal + `meta.data`;
- при желании агента — `train_nca` на своей полке (отдельный вызов, не gate).

Агент **не обязан** знать про JSONL vs `.ltm`.

---

## Recall

```text
agent_recall(query?, tags?, concepts?, limit?)
```

Возвращает **унифицированные записи** (из индекса + при необходимости decode полок). Не «иди в journal CLI» / «иди в prism CLI».

---

## Встраивание в tick (не MCP)

| Место | Вызов |
|-------|--------|
| Act / CEN | `agent_remember` по решению агента |
| После compose / surprise | opt-in self retain (не profile Extract) |
| End of tick batch | `save_runtime_state` (checkpoint) + self tier |

**MCP** — опциональный **внешний** транспорт для IDE; ядро вызывает **Python API** (`agent_memory_ops`), как `append_episode`.

### TickOrchestrator (v0, 2026-05-31)

Единая macro tick T — `casa/prisms/tick/orchestrator.py` (`run_learning_tick`), CLI: `python -m casa.prisms.control.agent_sn_cen_tick`.

```text
  decode field ──► act NCA rollout (memory lattice) ──► SN/CEN
       │                    │
       └── predict/surprise ┴──► hippo episode (Extract)
       └── opt-in agent_remember (explicit)
       └── sleep every N / on high value (Remember)
       └── optional Kolb batch (--kolb-session)
       └── save_runtime_state
```

| Фаза UC | Реализация |
|---------|------------|
| **Use** | `act_rollout_phase` — k-step NCA на active memory lattice |
| **Extract** | `surprise_to_hippo_episode` при `control.value ≥ threshold` |
| **Remember** | `run_sleep` по `--sleep-every` / `--sleep-on-value` |
| **Explicit** | `agent_remember` при surprise ≥ `remember_min_value`; **`agent_retain`** при self-verify predict |

Kolb CE→RO→AC→AE остаётся в `kolb_cycle.py` (сегментация); в orchestrator — opt-in hook, не каждый tick.

---

## CIDE host (без lab в поставке)

**CIDE** = host + verify + human lens; **CASA core** = substrate. Lab (`train_*`, export, bench) — **не** в IDE bundle; **runtime core + store на диске пользователя** — да.

```text
  %AppData%/…/agents/{profile-id}/     (пример; точный path — в profile manifest)
  ├── ltm/ + nca/          ← shipped (read-mostly, decode)
  ├── field_state.json     ← runtime checkpoint (неявное + hippo)
  ├── agent_session.json   ← WM
  ├── journal/             ← явный self (растёт локально)
  └── agent/               ← spatial self (опционально)
```

| Режим в IDE | Что происходит | Lab нужен? |
|-------------|----------------|------------|
| **Perceive / decode** | read shipped profile, digest | нет |
| **Фон tick** | predict, hippo, SN, checkpoint flush | нет (core API) |
| **Явно запомнить** | `agent_remember(record)` → journal/agent | нет |
| **Явно вспомнить** | `agent_recall` (+ opt. `include_field`) | нет |
| **NCA train на self-полке** | `train_nca` / фоновая job | опционально / offline |
| **В учебник profile** | `agent_promote` → sleep → export | да, batch/CI |

Hot path IDE → **core API** (`Remember` / `Recall` / `SaveRuntimeCheckpoint`), не `python -m casa.cli`. C# act/ORT — [`CASA-ADR-0007`](CASA-ADR-0007-agent-profile-store-packs.md); FieldBus — [`CASA-ADR-0012`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md).

**Roadmap tick в CIDE:** фоновый substrate через `run_learning_tick` **всегда**; `agent_remember` — когда CEN/политика решила «зафиксировать для сознательного recall», поверх уже накопленного неявного слоя.

---

## Promote (явно)

Перенос self → profile (`ltm/`, F0, L2, control stack): **отдельная** операция `agent_promote` (roadmap). Самопамять по умолчанию **остаётся** у агента.

### Self-modification control (см. ADR-0014)

Агент может завести **`agent-control-*`** решётку и **`agent_bridge`** к существующим `prism_control` / `prism_memory` — тогда routing **не в пустоту**, без молчаливого patch profile. Детали: [`CASA-ADR-0014-agent-prism.md`](CASA-ADR-0014-agent-prism.md) § Self-modification.

---

## Non-goals

- Жёсткая таксономия kind/domain как обязательный API.
- Авто-promote каждой self-записи в `prism_memory`.
- Дублирование UC Extract для self-tier.
- Сводить всю память агента к `journal/` (см. § Неявная vs явная).

Код v0: `casa/prisms/memory/agent_memory_ops.py` · `agent_workbook.py` (draft/check) · `agent_promote.py` (Self→profile) · persist: `casa/prisms/shared/store_persist.py` · CLI: `agent_remember`, `agent_recall`, `agent_workbook`, `agent_promote`.
