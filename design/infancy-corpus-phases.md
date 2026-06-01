# Infancy corpus phases v0 — «взросление» субстрата (не белый шум)

**Date:** 2026-05-30  
**Status:** accepted (design); **lab matrix** частично реализована — см. § «Сегодня vs roadmap»  
**Parent:** [`language-acquisition-loop.md`](language-acquisition-loop.md), [`bukvar-text-modality.md`](bukvar-text-modality.md)  
**Companion:** [`agent-store-catalog.md`](agent-store-catalog.md), [`lexicon-usage-axes.md`](lexicon-usage-axes.md), [`ru-lexicon-modern-archaic.md`](ru-lexicon-modern-archaic.md)

---

## Вопрос (из диалога)

На этапе «младенчества» субстрат получает **абсолютно хаотичный** текстовый поток (белый шум), чтобы решётки научились **проводить сигнал**, или **сразу** структурированные сказки, чтобы с первых тиков цепляться за **ритмику** речи?

**Ответ v0:** ни то, ни другое в чистом виде.

```text
  Фаза 0 — проводимость     immutable L0 + stack (не шум букв)
  Фаза 1 — фонотактика      букварь B0–B1, повторы слогов
  Фаза 2 — listen mass      сказка/корпус целиком, БЕЗ quiz
  Фаза 3 — babble→correct   учитель, minimal pairs
  Фаза 4 — sleep / DMN      кристаллизация hub (ветер↔ветяр)
  Фаза 5 — prod surface     T9/IDE + оси usage (modern hot path)
```

**Белый шум** — только **stress-test** repair (damage→recovery), не педагогика языка.

---

## Метафора ↔ инженерия

| Образ (субстрат «ребёнок») | CASA (не метафизика) |
|----------------------------|----------------------|
| Похожие волны на одних клетках | Co-activation на L0→L2; windowed NCA сближает соседние токены на tile |
| «Первичный бульон», нет понятия «ветер» | Particular `W:ветер`, `W:ветяр` на L2; **Form** = hub после Extract/sleep |
| DMN резонирует в тишине потока | `T_consolidate`, digest, hippo→prism_memory; не tabula rasa на запрос |
| Грамматика = русла на решётке | `R:context.*`, ortho после mismatch; не § grammar в hot path |
| RU/BY диалект = одна мелодия | **Цель:** merge по co-activation; **v0:** `era`/`archaic` в sidecar + lab store |
| SN замечает одинаковые маркеры окружения | Salience + episodic; bench кластеров — roadmap |

См. [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md), [`agent-existence-north-star.md`](agent-existence-north-star.md).

---

## Фазы (нормативный порядок)

### Фаза 0 — Wiring (проводимость среды)

| | |
|---|---|
| **Корпус** | Нет «случайного unicode». **Immutable alphabet** на `L0_grapheme_*` ([`alphabet-core-immutable.md`](alphabet-core-immutable.md)). |
| **Режим** | Imprint graphemes; опц. NCA repair на пустом/разреженном L2. |
| **Цель** | Решётка **проводит** сигнал и **чинит** раскладку, не «понимает сказку». |
| **Не делаем** | Белый шум как единственный вход — нет повторяемых аттракторов. |

### Фаза 1 — Babble phonotactics (букварь)

| | |
|---|---|
| **Корпус** | `kb-bukvar-*`, слоги «ма/па», алфавитный поток; symbolic cue v0 ([`CASA-ADR-0004`](CASA-ADR-0004-listen-modality-bukvar-sound.md)). |
| **Режим** | Listen B0→B1; surface/babble **без** штрафа за первую ошибку. |
| **Цель** | Basins на **графеме и слоге**, не на 50k леммах. |
| **Bench (TBD)** | listen→`grapheme.*` / `syllable.*` hit rate. |

Лестница: [`bukvar-text-modality.md`](bukvar-text-modality.md) B0–B3.

### Фаза 2 — Listen mass (сказка, поток)

| | |
|---|---|
| **Корпус** | **Целые тексты**: Afan shards (`ingest-ref-afan` ingest ref), dialogue KB, будущий `listen_mass/manifest.ndjson`. |
| **Режим** | Batch **encode в цилиндр**, не exam-QA; teacher **не** требует ответа на каждый токен. |
| **Цель** | Повторяющиеся n-граммы, контекстные «маркеры окружения»; co-activation **ветер / ветяр / …** на соседних tiles. |
| **Prod** | Modern DetCorpus **не заменяет** сказку для dialect merge — только **частотный** hot path. |

**Да:** сказку погружаем **рано**, как **listen**, не как словарный экзамен.

### Фаза 3 — Babble → correct (учитель)

| | |
|---|---|
| **Корпус** | Minimal pairs, «не ветяр, а ветер в этой сцене», dialogue + rules **как речь**. |
| **Режим** | Critic → windowed NCA на **том tile**, где ошибка; `field_version↑`. |
| **Цель** | Сдвиг поля, не новый claim «для ответа пользователю». |
| **Bench** | Held-out babble после 1–3 correct ([`understanding-contract.md`](understanding-contract.md)). |

Контур: [`language-acquisition-loop.md`](language-acquisition-loop.md).

### Фаза 4 — Sleep / DMN (кристаллизация)

| | |
|---|---|
| **Триггер** | Внешний поток затих (`T_consolidate`, gate). |
| **Механизм** | DMN digest → Extract → hub `entity.*` / `form.*`; укрепление LTM. |
| **Цель** | **Статистически** схлопнуть диалектные поверхности в один attractor, если co-activation устойчива. |
| **Bench v1** | Разделимость кластеров, не ключ `tags` в manifest (ADR-0003). |

**Сегодня:** control stack + hippo design есть; **авто-merge ветер↔ветяр** — roadmap.

### Фаза 5 — Prod surface (T9 / IDE)

| | |
|---|---|
| **Store** | `lexicon-ru-general` (modern), profile `ru_lexicon`. |
| **Оси** | `lexicon_axes.jsonl`: `active_for_t9`, `era`, `usage_band` — **фильтр predict**, не тег на клетке. |
| **Archaic** | `lexicon-ru-archaic` / Afan — **lab**, не prod hot path. |

См. [`lexicon-usage-axes.md`](lexicon-usage-axes.md), [`ru-lexicon-modern-archaic.md`](ru-lexicon-modern-archaic.md).

---

## Матрица корпусов и stores

| Фаза | Корпус / источник | Store (v0) | Скрипт / инструмент | Profile role |
|------|-------------------|------------|---------------------|--------------|
| 0 | immutable alphabet | любой RU store после imprint L0 | `grapheme_ingest`, quad init | — |
| 1 | bukvar KB | `bukvar-lab`, bundles | ingest bundle, listen_tick (roadmap) | listen (future) |
| 2 | Afan tales (sharded) | `ingest-ref-afan` (ingest ref), `lexicon-ru-archaic` | parallel ingest, **listen-only** mode TBD | — (не `ru_lexicon` prod) |
| 2b | DetCorpus 50k (modern) | `lab/corpus/ru-general/` | `build_lexicon_usage_axes.py` | источник для general |
| 3 | dialogue + grammar KB | `language-agent-lab` | Exp J train windowed | lab |
| 4 | — | тот же store после sleep | `T_consolidate` / hippo pipeline TBD | — |
| 5 | merged modern headwords | `lexicon-ru-general` | `scripts/run_sss_ru_general.ps1` | `ru_lexicon` |

**Правило:** имя корпуса (Afan) **не** в prod store_id; tier `archaic` vs `general` — в [`agent-store-catalog.md`](agent-store-catalog.md).

---

## Сегодня vs roadmap

| Возможность | Статус (2026-05-30) |
|-------------|---------------------|
| Immutable L0 + split cyrl/latn | ✅ |
| Batch imprint L2 + NCA CUDA shards | ✅ (`lexicon-ru-general`, `lexicon-ru-archaic`) |
| Listen mass → encode без quiz | ⚠️ design + ADR-0004; batch driver не канонизирован |
| Авто-hub ветер↔ветяр после listen | ❌ roadmap (Extract/sleep) |
| Babble→correct на held-out | ⚠️ Exp J partial (grammar/literacy), не dialect merge |
| `lexicon_axes` prod filter T9 | ✅ sidecar + `predictor` |
| Bench T9 только на `active_for_t9` | ❌ fix needed (prod policy vs full L2 eval) |
| Белый шум как фаза 0 | ❌ **не** в плане |

---

## Белый шум (явный запрет как педагогика)

Допустимо **только**:

- тест **damage→recovery** NCA ([`experiment-j-windows-ablation-v1.md`](experiment-j-windows-ablation-v1.md) и аналоги);
- проверка, что immutable L0 не «плывёт» под мусором.

**Недопустимо** как замена фаз 1–2: случайные строки без фонотактики и без повторов — субстрат учит **repair шума**, не **ритм языка**.

---

## Диалекты и «одна мелодия»

| Слой | v0 (инженерия) | North star |
|------|----------------|------------|
| Ingest | Отдельные `W:*` на L2; Afan в archaic store | — |
| Runtime prod | `t9_policy=prod` + `active_for_t9` | — |
| Понимание | Оси `era=archaic` в JSONL (среда для нас) | Один hub после фаз 2–4 |
| BY/RU фонетика | Не автоматический merge | Co-activation + correct в контексте сказки |

Lab-эксперимент «после listen+correct+sleep cue `вет…` → один hub» — отдельный bench (см. ADR-0003 § bench v1).

---

## Предлагаемые lab-скрипты (roadmap)

| Скрипт | Фазы | Заметка |
|--------|------|---------|
| `run_infancy_phase0_wiring.ps1` | 0 | L0 imprint + repair smoke |
| `run_infancy_phase1_bukvar_listen.ps1` | 1 | symbolic listen B0–B1 |
| `run_infancy_phase2_afan_listen_mass.ps1` | 2 | ingest encode **без** L2 quiz; store `lexicon-ru-archaic` или listen tier |
| `run_sss_ru_general.ps1` | 5 | уже есть: axes + init + NCA + bench |
| `bench_infancy_cluster_merge.py` | 4 | dialect pair list → cluster purity |

Имена — placeholder до реализации; контракт фаз — этот документ.

---

## Связь с profile «Language child»

В [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md):

| Pack | Stores | Фазы |
|------|--------|------|
| **Language child (full)** | RU general + listen mass tier | 0→2→3→4→5 |
| **BiT9 console** | `lexicon-ru-general` only | в основном **5** (surface/T9) |

Не смешивать: prod T9 profile **не** подмешивает Afan без явного `t9_policy=lab`.

---

## Checklist перед новым «infancy» экспериментом

- [ ] Указана **фаза** 0–5 (не «просто ещё корпус»)
- [ ] Режим **listen** vs **correct** vs **sleep** записан в manifest
- [ ] Store tier согласован (`general` не тянет archaic в prod merge)
- [ ] Метрика: repair / listen hit / cluster / T9 — не paste@1 на тех же фразах
- [ ] Запись в `lab/agent-stores/INDEX.md` + при необходимости `catalog.json`

---

## Для агента (Cursor)

При идее «дай ребёнку белый шум» — отсылать сюда: **фаза 0 = immutable L0**, **фаза 2 = сказка listen mass**.  
При «ветер/ветяр» — **сейчас** оси и lab store; **цель** — фаза 4 без словаря дизайнера.  
При коммите store — не путать **импринт L2** (скелет v0) с **выращенным** hub (roadmap).
