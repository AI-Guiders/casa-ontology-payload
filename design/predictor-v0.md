# Predictor v0 — внутренняя симуляция на поле

**Статус:** design (перед Exp L F1/F2 compose и UC v0.5)  
**Дата:** 2026-05-30  
**Родитель:** [`understanding-contract-v0.md`](understanding-contract-v0.md) § Predictive cognition  
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
| babble digest-only | predict **перед** act на каждом тике |
| | predict → **Critic** → Extract |

**Решение:** спроектировать и реализовать **Predictor v0** на **простом домене** (segment или F0 schema), **потом** F1/F2 compose (`cow+cow` → `M:qty:2×cow`). Иначе арифметика снова станет «bench распознавания», а не мышления.

---

## Одна строка

**Predictor** — подсистема, которая по cue + текущему полю возвращает **явное ожидание** (`hypothesis`) и **confidence**, опираясь только на grid + NCA steps + decode, **без** `claim.text`.

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
  ┌─ PREDICTOR v0 ─────────────────────────┐
  │  decode → digest                         │
  │  forward: babble | segment | rank | compose│
  │  out: Prediction { hypothesis, … }       │
  └──────────────────┬───────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ACT / articulate        CRITIC (v0.5+)
    (optional ext)          compare vs observation
                            pass → Extract
                            fail → ASK / surprise
```

Predictor **не** пишет в LTM и **не** обучает NCA_rule — только **read-mostly** forward pass + structured output для Critic и CEN.

---

## Тип `Prediction` (контракт)

```json
{
  "schema_version": 1,
  "modality": "segment",
  "cue": "встреча",
  "hypothesis": "встре|ча",
  "hypothesis_tokens": ["встре", "ча"],
  "digest": { "active_rules": [], "concept_ids": [], "math_tokens": [] },
  "confidence": 0.72,
  "lattice_ids": ["L1_syllable", "L3_phrase"],
  "nca_used": ["L1_syllable"],
  "provenance": { "engine": "segment_hypothesis" }
}
```

| Поле | Назначение |
|------|------------|
| `modality` | см. таблицу модальностей |
| `hypothesis` | строка или canonical token для сравнения Critic |
| `hypothesis_tokens` | structured (сегменты, `M:`, слоты) |
| `digest` | snapshot SN/digest **на момент predict** (audit + Critic coherence) |
| `confidence` | 0…1 из votes / verify / SN (не fake — low ok) |
| `nca_used` | какие repair-NCA прогнали (lexicon; rule-NCA — v1.4) |

---

## Модальности (v0 → v1)

| modality | cue | hypothesis engine | Lab зачаток | Bench v0 |
|----------|-----|-------------------|-------------|----------|
| **`segment`** | слово | `segment_hypothesis` + `verify_segment` | `sss_hypothesis_v0.py` | held-out слова, syllable match |
| **`surface`** | контекст + слот | `sss_babble_v0` / bukvar babble | partial | dative form после «согласно» |
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
modality surface → sss_babble path (digest-only)
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
| Oracle | rank после decode | `Prediction.hypothesis` vs `expect` |
| Surprise | нет | mismatch → event для Critic stub |
| Claims | off | off |

Exp L0 остаётся **regression** для F0 ingest; predict bench — **новый** критерий UC v0.5.

---

## Exp T9 — проверка на словах (без арифметики)

После **`predictor_v0`** можно **остаться на словах** и повторить логику **T9** (predictive text): пользователь даёт **неполный / двусмысленный** ввод → система **угадала слово** из поля, не из grep по KB.

### Маппинг T9 → CASA

| T9 (телефон) | CASA (поле) |
|--------------|-------------|
| нажатия 2-2-8 → «act», «cat», «bat» | **prefix / key-seq cue** → несколько `W:` кандидатов на L2 |
| словарь + частота | **votes** на grid (`grapheme`, `syllable`, `H:` tokens) |
| выбранное слово подсвечивается | **Prediction.hypothesis** = top word/segment |
| следующая буква уточняет | **новый cue** → predict снова; Critic при финале |

**Не нужны** цифры 2-9 в v0 — достаточно **prefix cue** по RU lexicon (`sss-ru-lexicon-v0`):

```text
cue: "пр"     → predict: приказ | привет | …  (rank by field)
cue: "прик"   → predict сужается
observation: "приказу" (teacher / T9 complete) → critic pass/fail
```

Третий режим — **segment T9**: неполное слово / «лепет» → `segment_hypothesis` + `compete_hypotheses` (`sss_field_hypotheses_v0`) — уже multi-hypothesis на поле.

### Modality `t9` (alias `prefix_word`)

```python
predict(state, cue="прик", modality="t9", min_prefix=2)
# → hypothesis top word, ranked candidates[], confidence
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
