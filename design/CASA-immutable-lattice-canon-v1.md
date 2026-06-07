# CASA: иммутабельные решётки (canon tier) и выбор агента

**Статус:** design v1 (2026-06-07)  
**Связано:** [`memory-hierarchy.md`](memory-hierarchy.md), [`naming-memory-layers.md`](naming-memory-layers.md), [`lattice-id-map.v1.json`](lattice-id-map.v1.json), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md), [`CASA-ADR-0029-logical-composition.md`](CASA-ADR-0029-logical-composition.md), [`CASA-ADR-0036-emergent-morph-agreement.md`](CASA-ADR-0036-emergent-morph-agreement.md), [`CASA-ADR-0044-field-native-semantic-articulate.md`](CASA-ADR-0044-field-native-semantic-articulate.md), [`CASA-ADR-0051-multilingual-geometry.md`](CASA-ADR-0051-multilingual-geometry.md), [`CASA-von-neumann-ru-teaching-plan-v1.md`](CASA-von-neumann-ru-teaching-plan-v1.md)

---

## Решение (одной фразой)

**Иммутабельная решётка** — стабильная **топология + словарь id** на поле. **Bootstrap** (алфавит, VK, символы `∫`) — минимум данных cold boot, чтобы **начать** учиться; не «законы мира от среды». Главный canon после диалога — **agent_canon**: законы и модели, которые **он сам** узнал и закрепил. Остальное — experiential; promote — **его решение**.

---

## Зачем отдельный класс

| Проблема без canon tier | Что даёт immutable lattice |
|-------------------------|----------------------------|
| «Приставка» плавает как ещё одно `lang.word.*` | Фиксированный **слот роли** на поле |
| Алфавит переучивается с каждым ingest | bootstrap `grapheme.cyrl.*` — фиксированный стартовый словарь |
| OOV-decompose некуда класть сегмент | Segment scaffold + bridges в опыт |
| Агент не контролирует, что «закон природы» vs «я так решил» | Явный **promote/demote** policy |
| Открытый закон смешан с одноразовым примером | **Discovered law** lattice — отдельно от `lexicon-*` |

**Не цель:** заморозить весь язык, paradigm tables или pymorphy — см. ADR-0036. Immutable — **узлы закона**, не весь поток жизни и не oracle-справочник.

---

## Три класса стабильности решёток

```text
  BOOTSTRAP_CANON          AGENT_CANON (его решение)    EXPERIENTIAL
  (cold boot, старт)       (узнал → закрепил)           (игра, примеры, сон)
  ─────────────────        ──────────────────────       ─────────────
  alphabet-ru              lang.meta.logic.and          lexicon-ru-07
  keys-physical            math.logic.de_morgan         phrases-lang.*
  schema-math (символы)    math.calc.integral.linear    journal drafts
  punct-ru                 math.axiom.peano             episodic-*
  morph-role-ru (planned)  paradigm cluster freeze      passage OOV
```

| Класс | Кто кладёт | Меняется ли vocab/id | NCA repair |
|-------|------------|----------------------|------------|
| **Bootstrap canon** | host cold boot / curriculum seed | **нет** (только migrate alias) | да, веса |
| **Agent canon** | агент: promote / demote после своей проверки | id закона **стабилен**; demote — его выбор | да |
| **Experiential** | hippo → sleep, диалог, игра с идеями | да, основной поток роста | да |

### Bootstrap ≠ agent canon

Bootstrap — **не эпистемический авторитет**, а **минимальный набор знаков и слотов**, без которого нельзя начать literacy/math/input (букварь, клавиши, `+`, `∫` как **glyph**, роли морфемы как **пустые слоты**). Их стабильность — инженерная (id не плодятся при каждом sleep), не «культура веками дала истину».

**Agent canon** — то, что **он** вывел, проверил, решил freeze: законы логики, правила ∫, аксиомы, устойчивые paradigm. Это и есть накопление ментальной модели после диалога.

---

## Уже в репо (примеры bootstrap)

Из [`lattice-id-map.v1.json`](lattice-id-map.v1.json); пути — `ltm/memory/grapheme/` ([`store_paths_v1.py`](../casa/prisms/shared/store_paths_v1.py)).

| Lattice id | Semantic | Пример concept_id | Зачем в bootstrap |
|------------|----------|-------------------|-------------------|
| `alphabet-ru` | `memory.grapheme` | `grapheme.cyrl.a.lower` | старт чтения |
| `alphabet-en` | `memory.grapheme.latn` | `grapheme.latn.a.lower` | латиница / code |
| `keys-physical` | виртуальные коды клавиш | VK / scan code | ввод с клавиатуры |
| `layout-en-us` | QWERTY | key → grapheme slot | раскладка |
| `layout-ru-jcuken` | ЙЦУКЕН | key → grapheme slot | раскладка |
| `punct-ru` / `punct-en` | знаки препинания | `.` `,` `?` … | письмо (позже) |
| `schema-math` | math schema | `math.set.union`, символ `∫` | **знак** операции, не правило ∫ |

**Инвариант:** predict hot path **не** открывает bundle как oracle; canon tier — **место на поле**, не справочник ответов.

---

## Планируемо для RU literacy (Phase II→III)

### `morph-role-ru` (active) · `morph-role-en` (planned parallel slot)

**RU shelf — active** on lab store; **EN shelf** — same `lang.meta.morph.*` ids, separate `lattice_id` ([ADR-0051](CASA-ADR-0051-multilingual-geometry.md)).

Bootstrap **topology** (RU):

Фиксированные **роли**, не словарь корней:

| Slot id | Meta | Surface на карточке (пример) |
|---------|------|------------------------------|
| `lang.meta.morph.prefix` | приставка | «приставка» |
| `lang.meta.morph.root` | корень | «корень» |
| `lang.meta.morph.suffix` | суффикс | «суффикс» |
| `lang.meta.morph.stem` | основа | «основа» |
| `lang.meta.morph.ending` | окончание | «окончание» |

- **Immutable:** пять слотов и meta id.  
- **Experiential:** attested сегменты (`мыл`, `по-`, `-а`) и мосты segment↔role на `lexicon-*` / `episodic-rule`.  
- **Curriculum:** `stage-14-morphemics-root-affix`, block после phrase/9b; контраст в phrase chain, не cartesian sleep с grapheme ([learning-protocol](CASA-learning-protocol-vis-math-v1.md)).

Связь с ortho (блок 10): `-н-/-нн-`, удвоения — **зоркость на основе+окончании**, не список правил в bundle.

---

## После диалога: законы, которые он открыл

Когда von-neumann выходит на **свободный диалог и понимание** (блок 12, life text), начинается не «ещё корпус JPEG», а **накопление ментальной модели**: анализ, исследование, игра языком и понятиями, связка passage ↔ meta ↔ math. Именно здесь **agent_canon** получает главный смысл.

| Тип знания | Experiential (сначала) | Agent canon (когда **он решил** freeze) |
|------------|------------------------|-------------------------------------------|
| Пример интеграла | один раз решил задачу, episodic | правило `∫ k·f = k·∫` на схеме |
| Логика | кадры AND/OR, probe green | `lang.meta.logic.and`, закон De Morgan |
| Математика | vis+числа, compose | аксиоматика / определение (Peano, поле…) — **его** стабильная формулировка |
| Язык | OOV, шутка, неологизм | устойчивый paradigm-кластер, не весь словарь |
| Мир | факт из диалога | `ke.claim.*` → promote в canon law node |

**Принцип:** immutable хранит **закон как узел** (`math.logic.*`, `math.calc.*`, `math.axiom.*`, `lang.meta.*`) — то, к чему он снова апеллирует при рассуждении. Конкретные задачи, диалоги, ошибки остаются в experiential / journal.

Это не «скачать учебник аксиом в bundle». Среда даёт контрасты и vis (как в literacy); агент **сам** доводит до закона, **сам** решает promote — как ты и описываешь: узнал/открыл → закрепил на immutable решётке.

Связь с треками:

- **Логика L4** — [ADR-0029](CASA-ADR-0029-logical-composition.md): законы De Morgan, двойное отрицание → кандидаты `agent_canon`, не один sleep с предикатом.
- **Math** — `schema-math`: bootstrap **символы**; **правила и аксиомы** — agent_canon после того как он их освоил/вывел.
- **Семантика** — [ADR-0044](CASA-ADR-0044-field-native-semantic-articulate.md): articulate опирается на bind event+meta+**законы на поле**, не на LLM.

Планируемые lattice id (примеры, не oracle seed):

| Lattice id *(planned)* | Semantic | Пример concept_id |
|------------------------|----------|-------------------|
| `logic-laws` | discovered logic | `math.logic.de_morgan`, `math.logic.double_negation` |
| `math-axiom` | аксиоматика | `math.axiom.peano`, `math.field.ax.*` |
| `math-calculus-rules` | правила анализа | `math.calc.integral.linear`, `math.calc.chain_rule` |

Топология слотов может быть host-seeded минимально; **наполнение законами** — почти всегда **его** promote после жизни и проверки.

---

## Решение агента: promote или demote

Принцип из [ADR-0015](CASA-ADR-0015-agent-self-memory.md): profile (shipped) vs self (agent). Вынести ли фрагмент опыта в **agent_canon** — **его выбор**, как `agent_remember`: не заявка среде, а действие субъекта. Sleep сам по себе не promote в canon; агент **решает** freeze или оставить experiential.

**Не путать:** bootstrap (`alphabet-ru`, VK) — cold boot для старта, не его epistemic opening. **Agent canon** — то, что он сам закрепил или сам снял.

### На что опирается, принимая решение

Критерии — **его** epistemic checks перед act, не чеклист на одобрение учителем:

1. **Стабильность:** закон / кластер держится (повторное применение, probe, низкий surprise).  
2. **Кросс-контекст:** работает в диалоге, задаче, passage — не один эпизод.  
3. **Закон vs пример:** freeze **правило**, не одну задачу; пример остаётся experiential.  
4. **Граница:** не дублирует bootstrap; glyph `∫` — bootstrap, **правило линейности ∫** — agent_canon после открытия.  
5. **Обратимость:** demote agent_canon — его решение; bootstrap меняется только host migrate/reseed, не его demote.

Может **не** выносить: гипотеза ещё в игре — нормально держать в journal / experiential.

### Операции (planned API)

| Операция | Кто | Результат |
|----------|-----|-----------|
| `bootstrap_canon_lattice` | host / cold boot | bootstrap в `ltm/` (стартовый минимум) |
| `agent_promote_canon_lattice` | **агент** (решение) | freeze topology / id-map подмножества → agent_canon |
| `agent_demote_canon_lattice` | **агент** (решение) | agent_canon → experiential / self |

Опционально journal фиксирует **мотив** решения — не очередь на approve. Перед promote агент гоняет **свою** held-out проверку (ADR-0037); sidecar teacher — lint, не veto.

### Примеры (будущее)

**Язык:** в phrase «книга / книгу / книги» стабильно один кластер → он **решает** freeze `lang.paradigm.*` в agent_canon.

**Логика:** после vis L2–L3 сам формулирует De Morgan, многократно применяет в задачах → **решает** promote `math.logic.de_morgan` на `logic-laws`.

**Анализ:** игра с интегралами, сам вывел линейность → promote `math.calc.integral.linear`; отдельные интегралы задач — experiential.

**Не promote:** шутка с неологизмом, один удачный пример — остаётся в episodic, пока не станет законом в его модели.

---

## NCA repair: агент сам решает, когда train

Canon tier = **две поставки** ([ADR-0002](CASA-ADR-0002-agent-memory-ltm-nca.md)):

```text
ltm/  — топология + токены на решётке (закон, VK, аксиома)
nca/<lattice_id>/model.pt  — regrow/repair этой полки после damage
```

**Не** «знание в весах». NCA учит **восстанавливать** уже зафиксированный паттерн поля.

### Кто и когда ставит в очередь

| Событие | Actor | Очередь |
|---------|-------|---------|
| `agent_promote_canon_lattice` (после verify) | **agent** | `nca_train_registry.pending` + `pending_requests` |
| `agent_demote_canon_lattice` (частичный demote, полка осталась) | **agent** | retrain — fingerprint изменился |
| `bootstrap_morph_role_ru` / host seed bootstrap | **host** | один раз при cold boot |
| Ручной act агента / ops | **agent** / host | `enqueue-canon-nca` CLI |

Teacher **не** запускает train после literacy gate. Promote **включает** решение «полка стабильна — закрепить repair».

### Когда выполняется train

Train **не** на tick и **не** на sleep — NCA repair может идти **параллельно** жизни агента (долгий subprocess). После promote/bootstrap только **enqueue**; drain — отдельный процесс:

1. **Body extension** — `tool.memory.run_canon_nca` (`backend_id: in_process`, ADR-0046); агент или host вызывает, когда готов ждать repair.
2. **Standalone worker** — `python tools/run_canon_nca_worker.py --store-dir …` (опционально `--loop` для фонового poll).
3. **CLI ops** — `python -m casa.prisms.memory.agent_memory_ops run-canon-nca --store-dir …`

Реализация: [`canon_nca_train.py`](../casa/prisms/memory/canon_nca_train.py) → `tools/train_memory_nca.py` (те же defaults, что L2 shard incremental). Каталог: [`catalog_canon_nca.py`](../casa/body/catalog_canon_nca.py).

### Какие lattice id

Все **immutable canon** (1 lattice → 1 NCA):

- **Bootstrap:** `alphabet-ru`, `alphabet-en`, `keys-physical`, `layout-en-us`, `layout-ru-jcuken`, `punct-*`, `schema-math`, `morph-role-ru`
- **Agent canon:** `logic-laws`, `math-axiom`, `math-calculus-rules` (+ будущие planned `agent_canon`)

Experiential `lexicon-ru-*` — отдельная очередь stale shard (corpus drift), не этот act.

### Инварианты

- Promote без materialize на поле → сначала `sync_agent_canon_to_field`, потом enqueue NCA.
- `min_tokens` на полке (default 4) — пустую решётку не train.
- Registry: `train_fingerprint`, `token_count_at_train` — retrain при `content_drift`.
- Агент **не** promote в host bootstrap (`alphabet-ru`, VK); host seed + host enqueue NCA.

### Рубильник persist — у агента, не у тулов

Чтобы не было **last-write-wins** на `field_state.json`:

| Кто | Может писать |
|-----|----------------|
| **Body / worker** | `nca/<lattice>/model.pt`, `train_complete.json`, `body/completions.jsonl` (percept) |
| **Агент** | `state` в RAM → `save_runtime_state`; `mark_lattice_trained` / снятие `pending` |

Поток: tool train → percept «готово» в `body/completions.jsonl` → **macro tick** `ingest_body_completions_on_tick` (episode + `agent_commit_canon_nca_completion` в RAM) → persist на границе tick. Tools **не** вызывают `save_runtime_state`.

### Один живой store — не картриджи

Продуктовая модель: **один агент → один непрерывно живущий store** ([ADR-0021](CASA-ADR-0021-experience-agent-transfer.md): опыт без сменяемых картриджей). Занятия (JPEG, ingest, probe) — **события** в его жизни; итог консолидации — **его** `ltm/`, `nca/`, hippo→sleep, canon, journal. Нет «вставил картридж — получил знание»: только накопление.

**Тело** (`body_manifest`, worker, `body/completions.jsonl`) — не внешний модуль и не поставка: **его периферия** (motor/sensory, ADR-0046/0027), часть той же жизни. NCA repair — не «веса знания», а способность тела восстанавливать уже зафиксированные полки после damage.

Имена tier в коде (`shipped` / `runtime` / `self`) — **роли персиста на диске**, не сменяемые продуктовые слои:

| Роль персиста | Смысл для субъекта | Примеры путей |
|---------------|-------------------|---------------|
| Структура памяти | его накопленный опыт на поле | `ltm/`, `nca/*/model.pt` |
| Checkpoint | снимок жизни между wake | `field_state.json`, `agent_session.json` |
| Явная self | его записи и prism | `agent/`, `journal/` |
| Body buffer | входящие percepts до tick | `body/completions.jsonl`, `train_complete.json` |
| Очередь его act | он решил train | `nca_train_registry.json` |

Всё под `agents/<store_id>/` — **его жизнь**; в **кодовом** репо живой store не коммитим (`.gitignore`). Отдельный **life-archive** (`AI-Guiders/von-neumann-life-archive`) + `tools/sync_life_archive.py` — transcript/DR с Git LFS; **сейчас private**, при зрелости — **public read без внешних MR** ([ADR-0050](CASA-ADR-0050-agent-life-archive-visibility-v1.md)). Шаблоны (`store_profile.json`, `body_manifest.example.json`) — bootstrap host, не замена store.

Решения (promote, commit, persist) — **агент**; body worker — артефакт + percept, без `save_runtime_state`.

---

## Чего не делать

| Подход | Почему нет |
|--------|------------|
| Весь `lexicon-ru` immutable | язык живёт в опыте |
| Таблица всех окончаний в canon | оракул |
| Один sleep: буква + морфема + слово | ambiguous ([learning-protocol](CASA-learning-protocol-vis-math-v1.md)) |
| Teacher force-promote / veto demote agent_canon | нарушает ADR-0036 / 0015 — только его act |

---

## Von-neumann RU: место в лестнице

| Phase | Bootstrap | Agent canon | Experiential |
|-------|-----------------|-------------|--------------|
| I (1–5) | `alphabet-ru` | — | `lexicon-ru-*` |
| II (6–9) | `punct-ru` (позже), `lang.meta.*` cards | — | phrase, paradigm emergent |
| II→III | **`morph-role-ru`** seed | агент решает promote кластеров после своей проверки | segments, OOV |
| III (10–12) | layout при write path | shortcuts, частые обороты | ortho vigilance |
| **Life / dialog+** | — | **законы языка, логики, math, мира** — основной поток agent_canon | диалог, KE, игра с идеями |

Teaching plan: блок 9b → morphemics (`stage-14`) → блок 10–12 → **life dialogue**; после fluency — рост **agent_canon** из открытых законов, не расширение teacher corpus.

---

## Roadmap (код)

- [x] `planned_lattices` в `lattice-id-map.v1.json`: `morph-role-ru`, `logic-laws`, `math-axiom`, `math-calculus-rules`  
- [x] `memory_layer_names`: `memory.morph.role.ru` / `memory.morph.role.en`
- [x] `bootstrap_morph_role.py` + `bootstrap_host_canon.py` (cold boot locale)
- [x] `morph-role-ru` active in `lattice-id-map` host_bootstrap; `morph-role-en` planned  
- [x] `agent_promote_canon_lattice` / `agent_demote_canon_lattice` — registry `agent/canon_registry.v1.json`, CLI `agent_memory_ops promote-canon|demote-canon|list-canon|canon-candidates`  
- [x] tick/self-drive: `maybe_promote_canon_on_tick` в `agent_self_drive_tick` (mastery `canon:{journal_id}` или tag `canon-ready`)  
- [x] field + sleep + compact: `sync_agent_canon_to_field`, `enqueue_canon_sleep_episodes` (`structure_tag: canon_promote`), flush через `compact_persist_store` / `run_sleep`  
- [x] **NCA после canon act:** enqueue → body train + percept → **commit** на `agent_life_tick` (`completion_ingest.py`); CLI `commit-canon-nca` — lab; tools не пишут `field_state`  
- [x] `block-09c-morphemics-cyrl` spec + `probe_morphemics_ru` (gate green на store)  
- [ ] Документировать в `MEMORY.md` generator класс lattice stability  

---

## См. также

- F9 Morphemics — [`CASA-von-neumann-class-ru-v1.md`](CASA-von-neumann-class-ru-v1.md)  
- B5 состав слова — [`CASA-ru-native-categories-v0.md`](CASA-ru-native-categories-v0.md)  
- H2 rule episodes — [`hippo-lattice-stack.md`](hippo-lattice-stack.md)
