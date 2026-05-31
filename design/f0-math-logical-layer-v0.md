# F0 — логико-математический слой (первая сигнальность)

**Статус:** design v0 (текст и схемы; vis — позже)  
**Дата:** 2026-05-30  
**Машиночитаемо:** [`f0-math-lattice-stack.v0.json`](f0-math-lattice-stack.v0.json)  
**Соседи:** [`sss-lattice-stack.v0.json`](sss-lattice-stack.v0.json) (вторая СС), [`experiment-l-concrete-to-abstract-v0.md`](experiment-l-concrete-to-abstract-v0.md), [`hippo-lattice-stack-v0.md`](hippo-lattice-stack-v0.md)

## Зачем отдельный слой

Пример: **одна корова + ещё одна корова = 2 коровы**.

| Что | Где живёт | Это не… |
|-----|-----------|---------|
| Звук/слово «корова», «две» | **L2** (ССС, `lang.word.*`) | логика |
| Картинка коровы | **F0_vis** (roadmap, `vis.animal.cow`) | счёт |
| **Слияние двух однотипных единиц → количество 2** | **F0…F2 math** (`M:unit:cow`, `M:qty:2×cow`) | орфография |

Язык **называет** результат; логический слой **хранит структуру операции** — modal-agnostic (палочки, коровы, яблоки — один `M:op:add` при одном `M:unit:*`).

Как в KB: **факты и связи**, не простыня — здесь **concept_id + рёбра**, не дублирование «корова» в десяти JSON-ячейках.

## Две сигнальности на одном цилиндре

```text
  prism_memory
  ┌─────────────────────────────────────────────┐
  │  F0_schema   F1_compose   F2_quantity      │  ← логика (1-я СС)
  │       \         |          /                │
  │        f_bridge (aggregate, same unit)      │
  │               concept_hub                    │
  │       /         |          \                │
  │  L0 … L2_word_XX … L3                      │  ← знаки (2-я СС)
  └─────────────────────────────────────────────┘
         vis (Exp L) ──E──► hub ──► F2 / L2
```

**Не смешивать** каналы ССС (`W:`, `C:lang.word.*`) с логическими (`M:inst:`, `M:qty:`) на одной решётке без маршрута SN.

## Стек F0…F2 (специалисты логики)

| id | f | Роль | Пример |
|----|---|------|--------|
| **F0_schema** | 0 | чистые схемы: `\|`, `\|\|`, `+`, `=` | `M:sym:two`, `M:op:add` |
| **F1_compose** | 1 | **рабочая зона**: экземпляры одной единицы | `M:inst:cow@a`, `M:inst:cow@b` |
| **F2_quantity** | 2 | **связанная величина** | `M:qty:2×cow` |

### Пример «корова + корова» (только текст, v0)

```text
1. L2 уже знает lang.word.cow («корова»).
2. SN/CEN: задача «сколько коров» / teacher «ещё одна корова».
3. F1_compose: два слота с M:unit:cow (ground из L2 через f_bridge_L2_F1).
4. M:op:add (из F0_schema) срабатывает при homogeneity (оба cow).
5. F2_quantity: M:qty:2×cow.
6. CEN + L2 + J grammar: articulation «две коровы» — через hub, не копипаста F2 в W:* без моста.
```

Тот же пайплайн для **палочек** без картинки: `M:unit:stick`, Exp L L0.

## Правила логической зоны (контракт)

| Правило | Смысл |
|---------|--------|
| **Однородность** | `M:op:add` только если `M:unit:*` совпадает (корова+корова ✓; корова+овца → отдельный урок / ошибка babble) |
| **Modal-agnostic** | `M:qty:2×cow` не содержит пикселей; `vis.*` — якорь через `E:`, не внутри M: |
| **Hub, не merge** | `lang.word.cow` и `M:unit:cow` — **ребро** `E:`, не одна строка в cells |
| **Homonymy** | «лук» (растение vs оружие) — **разные** `M:unit:*` / `concept_id`; disambiguation SN + контекст, не один shard L2 |
| **Sleep** | стабильные схемы F0 → hub; эфемерный F1 может очищаться после consolidate (как hippo → memory) |

## Мосты `f_bridge_*`

| Мост | Направление | Действие |
|------|-------------|----------|
| `f_bridge_F0_F1` | схема → экземпляр | «один» → один слот |
| `f_bridge_F1_F2` | compose → quantity | aggregate |
| `f_bridge_L2_F1` | слово → unit | ground «корова» |
| `f_bridge_F2_L2` | quantity → речь | name (CEN, не прямой dump) |
| `f_bridge_F2_vis` | quantity ↔ картинка | Exp L, roadmap |

Отличие от **z_bridge** (L0→L1 внутри ССС): z — **знак→знак**; f — **логика↔знак/образ**.

## Что можно сделать **сейчас** (без новых модальностей)

Остаёмся на **текст + поле**:

1. **L0 Exp L** — KB `math.*`, палочки `| ||`, bench schema@1.
2. **F0_schema** — те же claims как `M:sym:*` на отдельной решётке (codec v0).
3. **F1/F2** — smoke: два token `lang.word.cow` в cue → compose в F1 → `M:qty:2×cow` (скрипт/bench, без vis).
4. **H2_rule** (hippo) — ошибка «корова+овца» → rule episode, не ломать F2.

Vis и webcam **не блокируют** проектирование F-слоя.

## SN / CEN (логическая зона)

| Режим | active | Действие |
|-------|--------|----------|
| `compose` | F1_compose | разместить instances |
| `count` | F2_quantity | read qty |
| `compare` | F0_schema + F2 | больше/меньше |
| `name` | L2 + CEN | выдать текст по hub |

`active_subsystem`: `sss` | `first_signal_math` | `first_signal_vis` (later).

## Поставка и NCA

| Артефакт | Статус |
|----------|--------|
| `ltm/` для L2 | v0, [`ltm-pack-v0.md`](ltm-pack-v0.md) |
| `ltm/` для F* | roadmap (`ltm` или общий pack tier B) |
| NCA на F* | не обязательно per-lattice v0; union hub train позже |

## Roadmap

| Версия | Содержание |
|--------|------------|
| **v0** | design + JSON; Exp L0 symbols; bench без F1/F2 кода |
| **v1** | `F0_schema` lattice в field_state; ingest `kb-math-concrete-schemas` |
| **v2** | `F1_compose` + `F2_quantity`, `bench_math_compose_v0.py` |
| **v3** | hub edges + SN routing; homogeneity errors → hippo |
| **v4** | vis grounding (Exp L2+) через `f_bridge_F2_vis` |

## Non-goals

- Сырые пиксели или «нейросеть считает коров» на hot path.
- Замена Exp J grammar — склонение «две коровы» остаётся на L2/L3 + articulation.
- Один монолит `F0_math` без F0/F1/F2 — как отказ от шардов L2.

## Связанные документы

| Документ | Роль |
|----------|------|
| [`understanding-contract-v0.md`](understanding-contract-v0.md) | контракт понимания (Extract / Remember / Use) |
| [`experiment-l-concrete-to-abstract-v0.md`](experiment-l-concrete-to-abstract-v0.md) | куррикулум L0–L4, vis |
| [`second-signal-system-v0.md`](second-signal-system-v0.md) | граница 1-й / 2-й СС |
| [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md) | поставка памяти |
| [`bukvar-text-modality-v0.md`](bukvar-text-modality-v0.md) | порядок: язык → потом картинки |
| [`kb-math-development-evidence-v1.md`](kb-math-development-evidence-v1.md) | human numeracy evidence (agent-notes; deny → F0 oracle) |

## Пример цепочки (палочки → коровы — один механизм)

```text
F0  | + |  →  M:sym:two, M:op:add
F1  stick@a + stick@b  →  M:qty:2×stick
L2  «две палочки»  ←E→  M:qty:2×stick

F1  cow@a + cow@b  →  M:qty:2×cow
L2  «две коровы»   ←E→  M:qty:2×cow
L4  [vis cow]      ←E→  lang.word.cow  (позже)
```

Счёт и букварь — **одна логическая машина**, разный `M:unit:*`.
