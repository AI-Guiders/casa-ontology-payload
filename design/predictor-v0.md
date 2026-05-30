# Predictor v0 — внутренняя симуляция на поле

**Статус:** design (перед Exp L F1/F2 compose и UC v0.5)  
**Дата:** 2026-05-30  
**Родитель:** [`understanding-contract-v0.md`](understanding-contract-v0.md) § Predictive cognition  
**Канон T9:** [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md)  
**Соседи:** [`f0-math-logical-layer-v0.md`](f0-math-logical-layer-v0.md), [`experiment-l-concrete-to-abstract-v0.md`](experiment-l-concrete-to-abstract-v0.md)  
**Следующий:** `critic-v0.md` (roadmap), `bench_predict_v0.py`

---

## Зачем сейчас (до арифметики)

Exp L0 (`bench_math_schema_v0`) доказал **USE без claim.text**: cue → decode → **rank** `M:` на F0.  
Это **не** predict loop: нет явного **ожидания Y**, нет **surprise**, нет связки с Critic.

| Уже есть (UC v0.1) | Ещё не есть |
|--------------------|-------------|
| schema@1 rank на F0 | **Predictor** как модуль hot path |
| segment hypothesis (`sss_hypothesis_v0`) | единый API + bench |
| surface digest-only | predict **перед** act на каждом тике |
| | predict → **Critic** → Extract |

**Решение:** спроектировать и реализовать **Predictor v0** на **простом домене** (segment или F0 schema), **потом** F1/F2 compose (`cow+cow` → `M:qty:2×cow`). Иначе арифметика снова станет «bench распознавания», а не мышления.

---

## Одна строка

**Predictor** — не «вернуть объект с ответом», а **свести частичный cue к нескольким якорям на решётке** (конкуренция активаций). Следующая буква / контекст / Critic **сужает** множество; один «ответ» — только после focus, не на первом тике T9.

---

## Якоря, не объект `Prediction`

### Как **не** надо думать (v0.5 lab shortcut)

```json
{ "hypothesis": "мама", "confidence": 0.2 }
```

Это **удобный лог для bench**, но **не** модель данных hot path. Ответ не «лежит в JSON» — он **вспыхивает на поле** как набор якорей.

### Как **надо** (CASA)

На поле уже лежат **якоря** — размещённые токены, каждый = узел смысла:

| Токен | Якорь | Полка |
|-------|--------|-------|
| `W:мама` | слово как surface | L2 shard |
| `C:lang.word.мама` | понятие в lexicon | L2 |
| `M:qty:2×cow` | схема | F0 |
| `R:ru.case.dative…` | правило | L3 / H2 |

**Predictor** при частичном вводе **`ма`**:

```text
  cue "ма"  (grapheme band / partial Q: token — roadmap)
       │
       ▼
  активация с L0/L1 вверх по z-bridge / hub
       │
       ▼
  КОНКУРЕНЦИЯ якорей на L2 (не один победитель в JSON):
       W:мама   ████████
       W:майка  ██████
       W:маска  █████
       W:марля  ████
       …
```

T9 в телефоне делает то же: **список кандидатов**, пока не уточнили ввод. Critic / следующий символ / учитель **выбирают** из множества или оставляют ambiguity явной.

### Выход Predictor (целевой контракт)

**Первичный:** `AnchorActivation[]` на поле — **не** singleton `hypothesis`.

```json
{
  "cue": "ма",
  "anchors": [
    { "token": "W:мама", "concept_id": "lang.word.мама", "lattice_id": "L2_word_12", "activation": 0.82 },
    { "token": "W:майка", "concept_id": "lang.word.майка", "lattice_id": "L2_word_07", "activation": 0.71 },
    { "token": "W:маска", "concept_id": "lang.word.маска", "lattice_id": "L2_word_03", "activation": 0.68 }
  ],
  "focus": null
}
```

| Поле | Смысл |
|------|--------|
| `anchors[]` | **главное** — кого поле «подтянуло» к cue |
| `activation` | votes / field_score / softmax по конкурентам |
| `focus` | один якорь **только после** сужения (ещё буква, Critic pass, act) |

`hypothesis: "мама"` — **производное** (`anchors[0]` или `focus`), для bench и articulate, **не** источник истины.

### Связь с уже существующим кодом

| Идея | Lab сегодня |
|------|-------------|
| конкуренция якорей | `sss_field_hypotheses_v0.compete_hypotheses`, `Wh:{word}/{segment}` |
| слова на L2 | `W:`, `C:lang.word.*` в `ltm/` |
| T9 prefix list | `l2_prefix_candidates` → **`ranked`** (anchors без token/placement) |
| singleton `hypothesis` | **bench shortcut** — ref v0.6 |

### Якорь как крючок для смыслов (roadmap)

Predictor зажигает **не строку**, а **узлы на поле** — к ним уже сейчас (и дальше удобнее) **навешивается семантика**:

```text
  W:мама  ──hub──►  C:lang.word.мама
       │                  │
       │                  ├── E:…|gov|…     (управление, valency)
       │                  ├── R:ru.case…     (правило после «согласно»)
       │                  ├── L:scene|мама   (сцена / turn)
       │                  └── M:…            (abstract, F0/F2)
       │
       └── votes + placement на L2 shard  ← то, что видит predict
```

| Слой | Что «вешается» на якорь | Когда |
|------|-------------------------|-------|
| **surface** | `W:` + syllable/grapheme на L1 | lexicon, T9 |
| **concept** | `C:{concept_id}` | Extract / sleep |
| **relation** | `E:{src}\|rel\|{dst}` | правила, сцены, compose |
| **rule** | `R:{rule_id}` на L3 / H2 | teacher_correct → Remember |
| **unit** | `UnderstandingUnit.anchors` | атом «понял» после Critic pass |

**Почему multi-anchor predict важен:** пока cue = `ма`, активны несколько `W:*` — у каждого **свой** подграф смыслов. Сужение до `focus` = выбор **какой** subgraph участвует в act / articulate, не подмена одной строкой без структуры.

Смысл **не** хранится в `hypothesis` JSON — он **растёт от якоря** через sleep и hub edges ([`understanding-contract-v0.md`](understanding-contract-v0.md) § UnderstandingUnit).

---

## Место в контуре

```text
  cue / context
       │
       ▼
  ENCODE (optional write-band)
       │
       ▼
  NCA_repair (lexicon / rule patch if damaged)
       │
       ▼
  ┌─ PREDICTOR ──────────────────────────────┐
  │  decode: какие якоря зажглись             │
  │  out: AnchorActivation[] (top-K)         │
  │  НЕ: один JSON-ответ как истина           │
  └──────────────────┬───────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  ещё буква / context      CRITIC
  (сужает anchors)          observation vs anchor set
                            pass → focus + Extract
```

Predictor **не** пишет в LTM. **Focus** (один якорь) появляется после Critic или при достаточном cue — не в первом тике T9.

---

## Тип `Prediction` (legacy bench wrapper)

> **Deprecated as primary model.** Bench v0.5 сериализует `ranked` → `hypothesis` для `critic_validate`. v0.6: Critic работает с `anchors[]`, `focus` optional.

```json
{
  "schema_version": 1,
  "modality": "t9",
  "cue": "ма",
  "anchors": [
    { "token": "W:мама", "concept_id": "lang.word.мама", "activation": 0.82 }
  ],
  "hypothesis": "мама",
  "ranked": [["мама", 3], ["майка", 3]]
}
```

| Поле | Назначение |
|------|------------|
| `anchors` | **канон** (v0.6+) |
| `ranked` / `hypothesis` | совместимость bench v0.5 |
| `modality` | см. таблицу модальностей |
| `digest` | snapshot SN/digest на момент predict |
| `confidence` | spread по top-K anchors (не fake — low ok) |

---

## Модальности (v0 → v1)

| modality | cue | hypothesis engine | Lab зачаток | Bench v0 |
|----------|-----|-------------------|-------------|----------|
| **`segment`** | слово | `segment_hypothesis` + `verify_segment` | `sss_hypothesis_v0.py` | held-out слова, syllable match |
| **`surface`** | контекст + слот | `sss_surface_v0` / `bukvar_surface_v0` | partial | dative form после «согласно» |
| **`schema`** | `\|\|`, `math.add` | `rank_cue_on_f0` → top `M:` | `bench_math_schema_v0` | **self-predict**: top == expect без oracle rank-only |
| **`t9`** / **`prefix_word`** | `пр`, `прик` | L2 prefix + field votes | — | [`experiment-t9-predictive-words-v0.md`](experiment-t9-predictive-words-v0.md) |
| **`compose`** | `cow+cow` | F2 compose (roadmap) | — | **после** predictor+critic stable |

**Predictor v0 scope:** **`segment`** + **`schema`** (два bench, один модуль). Surface и compose — v0.5/v1.

---

## API (целевое)

```python
# tools/predictor_v0.py (planned)

def predict(
    state: dict,
    cue: str,
    *,
    modality: str,
    bundle: dict | None = None,
    lattice_id: str | None = None,
    nca_repair: bool = True,
) -> dict:
    """Returns Prediction dict; mutates state only if encode write-band enabled."""
```

Роутинг:

```text
modality segment → segment_hypothesis + format_segment
modality schema  → rank_cue_on_f0 (bundle + decoded F0)
modality surface → sss_surface path (digest-only)
modality compose → NotImplemented (F2)
```

---

## NCA на predict-тике

| Шаг | NCA | Когда |
|-----|-----|-------|
| Lexicon shelf repair | `NCA_repair` | optional, если damage / low decode |
| Rule patch repair | `NCA_rule` | v1.4, если активен `R:{rule_id}` |
| Forward steps | те же веса | k steps **перед** decode (как в Use) |

Predictor **не** смешивает repair-target и predict-target: repair восстанавливает layout; predict **читает** layout и строит hypothesis.

---

## Отличие от Exp L0 bench

| | `bench_math_schema_v0` (сейчас) | `bench_predict_v0` (целевое) |
|--|--------------------------------|------------------------------|
| Вопрос | «правильный `M:` **ранжируется** первым?» | «predict **выдал** Y; Y **совпало** с expect?» |
| Oracle | rank после decode | `expect` ∈ `anchors[]` или `focus == expect` |
| Surprise | нет | mismatch → event для Critic stub |
| Claims | off | off |

Exp L0 остаётся **regression** для F0 ingest; predict bench — **новый** критерий UC v0.5.

---

## Exp T9 — проверка на словах (без арифметики)

> **Канон:** архитектурные решения T9 — [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md). Ниже — краткое резюме; bench — [`experiment-t9-predictive-words-v0.md`](experiment-t9-predictive-words-v0.md).

После **`predictor_v0`** можно **остаться на словах** и повторить логику **T9** (predictive text): пользователь даёт **неполный / двусмысленный** ввод → система **угадала слово** из поля, не из grep по KB.

### Маппинг T9 → CASA

| T9 (телефон) | CASA (поле) |
|--------------|-------------|
| нажатия 2-2-8 → «act», «cat», «bat» | **prefix cue** → **несколько якорей** `W:*` на L2 одновременно |
| словарь + частота | **votes / activation** на grid |
| список кандидатов на экране | **`anchors[]`** — не один `hypothesis` |
| следующая буква уточняет | новый cue → **сужение** anchor set; Critic при финале → `focus` |

**Не нужны** цифры 2-9 в v0 — достаточно **prefix cue** по RU lexicon (`sss-ru-lexicon-v0`):

```text
cue: "ма"     → anchors: мама | майка | маска | марля | …
cue: "мам"    → anchor set сужается
observation: "мама" (teacher / T9 complete) → critic: expect ∈ anchors? → focus
```

Третий режим — **segment T9**: неполное слово / «лепет» → `segment_hypothesis` + `compete_hypotheses` (`sss_field_hypotheses_v0`) — уже multi-hypothesis на поле.

### Modality `t9` (alias `prefix_word`)

```python
predict(state, cue="прик", modality="t9", min_prefix=2)
# → anchors[] (ranked W: tokens), focus=null until narrowed
```

Engine: decode L2 shards matching prefix + field scores (не linear scan JSON KB).

### Bench `bench_t9_predict_v0.py` (planned)

| # | cue | expect (held-out) | pass |
|---|-----|-------------------|------|
| 1 | prefix «мам» | «мама» top-1 | predict + critic |
| 2 | ambiguous «согласно пр» | «приказу» после контекста L3 | surface + rule R: |
| 3 | segment «встре» | «встре\|ча» not «в\|стре\|ча» | после sleep + rule |

Метрики: **top-1@prefix**, **predict→critic pass rate**, ablation `claims_nav off`.

### Порядок относительно арифметики

```text
predictor_v0 (segment)
    → bench_predict segment
    → bench_t9 prefix (слова, L2)
    → critic_v0 stub
    → schema modality (F0, уже почти rank)
    → только потом F1/F2 compose
```

T9 на словах — **тот же** predict loop, что потом на `M:` и compose; пользователю и bench понятнее, чем сразу «корова плюс корова».

---

1. **`design/predictor-v0.md`** (этот файл) + **`design/critic-v0.md`** (stub)
2. **`tools/predictor_v0.py`** — segment + schema modalities
3. **`tools/bench_predict_v0.py`**
   - segment: 10 held-out слов (как hypothesis smoke)
   - schema: те же 5 cues Exp L0, но pass = `prediction.hypothesis == expect_top`
4. Wire в `store_boot_v0.py --smoke` опция `--predict segment|schema`
5. **Только после green bench:** F0→F1 sticks, `bench_math_compose_v0` (compose modality)

---

## Milestones (уточнение)

| ID | Deliverable | Блокирует |
|----|-------------|-----------|
| **UC v0.5a** | `predictor_v0.py` + `bench_predict_v0` segment | — |
| **UC v0.5b** | schema modality + smoke | F1 compose |
| **UC v0.5c** | `anchors[]` как первичный выход; Critic по множеству | — |
| **UC v0.6** | `critic_v0.py` stub (compare only) | NCA_rule train |
| **UC v1.3** | CEN clarify on critic fail | — |
| **UC v1.4** | NCA_rule after critic pass | — |
| **UC v2.0** | compose modality + Exp L F2 | — |

---

## Не делать в v0

- LLM на hot path
- Обучение NCA внутри predict
- Compose arithmetic до green predict+critic на segment/schema
- Путать rank@1 bench с predict loop

---

## Связь с KB

Epistemic: prediction that can fail → [`understanding-contract-v0.md`](understanding-contract-v0.md) § COMPREHEND.  
Org mirror: обновить после стабилизации API.
