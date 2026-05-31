# CASA-ADR-0006: T9 — predictive text на поле (prefix → anchors → focus)

**Статус:** accepted (lab green на prefix + letter loop; context L3 — roadmap)  
**Дата:** 2026-05-30  
**Область:** ССС / B2 слово / predictor / critic / unified tick  
**Связано:** [`predictor.md`](predictor.md), [`experiment-t9-predictive-words.md`](experiment-t9-predictive-words.md), [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md), [`understanding-contract.md`](understanding-contract.md), [`bukvar-text-modality.md`](bukvar-text-modality.md)

---

## Контекст

### Что такое T9 здесь

**T9** — не телефонная клавиатура 2–9, а **метафора predictive text**: неполный **prefix cue** → **несколько кандидатов-слов** на L2 → следующая буква или Critic **сужает** множество → **focus** на одном якоре.

Это **modality** в petле Understanding Contract (predict → critic → extract), тот же tick-router, что script / ortho / listen / unified.

### Почему отдельный ADR

T9 размазан по `predictor.md` и `experiment-t9-predictive-words.md`, но **архитектурные решения** (anchors vs hypothesis, focus, ambiguity, место в unified tick, claims off) нигде не были собраны в одном каноническом месте. Этот ADR — **источник истины** для T9; experiment-doc — bench и cues.

### Где в лестнице букваря

| Ступень | T9 роль |
|---------|---------|
| B0/B1 | **не** T9 — grapheme / syllable basins (listen, script) |
| **B2** | **основной слой T9** — `lang.word.*`, prefix по surface |
| B3 | **context T9** — prefix фразы + active `R:` (roadmap, см. §7) |

---

## Решение

### 1. Modality `t9` (alias `prefix_word`, `prefix`)

```python
predict(state, cue="мам", modality="t9", top_k=8)
# → anchors[] ranked, focus=null | one anchor, hypothesis=bench shortcut
```

| Поле выхода | Статус | Смысл |
|-------------|--------|--------|
| **`anchors[]`** | **primary** | конкуренция `W:*` на L2 — главный результат predict |
| `focus` | после сужения | один якорь, когда cue == top word **или** critic pass |
| `hypothesis` | **derivative** | `anchors[0].word` — для bench/log, **не** источник истины |
| `ranked` | debug/bench | `(word, votes)*` из L2 prefix index |

Реализация: [`predictor.predict_t9`](../tools/predictor.py), engine `l2_prefix_index_votes`.

### 2. Маппинг «телефонный T9 → CASA»

| T9 (телефон) | CASA (поле) |
|--------------|-------------|
| 2-2-8 → act, cat, bat | prefix `"пр"` → anchors: приказ, призыв, … |
| частота в словаре | **votes / activation** на L2 shard |
| список на экране | **`anchors[]`**, не singleton answer |
| следующая буква | новый cue → сужение set; final → critic → `focus` |
| завершил слово | `observation == expect` → critic pass |

**Цифры 2–9 в v0 не нужны** — достаточно Unicode prefix по lexicon в цилиндре (`sss-ru-lexicon`, bilingual stores).

### 3. Три режима cue (v0 + roadmap)

| режим | cue | expect | engine | lab |
|-------|-----|--------|--------|-----|
| **prefix** | `мам`, `прика` | одно слово top-1 / `expect` | `predict_t9` | **green** — `bench_t9_predict` |
| **letter loop** | `м`→`ма`→…→`мама` | target ∈ anchors, final pass | `simulate_t9_type` | **green** — `predict_tick` |
| **ambiguous prefix** | `ма`, `рос` | `expect_in` — множество допустимых | `predict_t9` + critic `expect_in` | **green** — manual cues |
| **context** | `согласно пр` | `приказу` (L3 + `R:`) | L3 phrase + rule votes | **roadmap** — experiment doc |
| **segment** | целое слово internal | `встре\|ча` | modality **`segment`**, не `t9` | отдельный bench |

**Segment ≠ T9:** segment режет **внутренность** слова; T9 **дописывает** surface слева направо. Оба multi-hypothesis, разные modalities.

### 4. Letter-by-letter loop (typing metaphor)

```text
  tick 1  cue "м"     → anchors: м… (≥2 кандидата — ambiguity ok)
  tick 2  cue "ма"    → anchors сужаются; target ∈ set когда prefix длинный
  …
  tick N  cue "мама"  → observation "мама", critic pass → focus
```

Контракт: [`predict_tick.simulate_t9_type`](../tools/predict_tick.py).

| Фаза prefix | pass criterion |
|-------------|----------------|
| короткий | `len(anchors) >= 2` (ещё не дисамбiguируем) |
| длинный / предфинал | `target in anchors` |
| финал | `critic verdict pass` + `focus` |

Это тот же UC loop, что teacher_correct — **повторяемые тики**, не один shot predict.

### 5. Critic contract (T9)

| critic arg | когда |
|------------|--------|
| `expect` | одно целевое слово (top-1 или full match) |
| `expect_in` | **ambiguous prefix** — любой из списка в anchors |
| `observation` | teacher ввёл полное слово — финальный tick |

**Claims nav off** на всех T9 bench — ответ только из **field/L2**, не grep KB.

Focus подставляется critic-ом при pass, если predict не выставил (`critic`).

### 6. Связь с ADR-0003 (emergent)

- T9 **не** создаёт новые `lang.word.*` при predict — **read-mostly** activation.
- **Extract** после surprise (новое слово в корпусе) — отдельный tick, не часть T9.
- Частотность / priors — **votes на grid**, не tag `freq: 0.8` в ingest.

### 7. Unified tick — T9 не изолирован

[`unified_tick.py`](../tools/unified_tick.py):

```text
  script (commit | ambiguous dual branch)
       │
       ▼
  T9 per branch (grapheme_string после homoglyph/script)
       │
       ├── optional ortho (surface Form)
       └── optional hub (entity neighbors)
```

| Сосед | Отношение к T9 |
|-------|----------------|
| **script_detect** | **до** T9 — какой алфавит / basin |
| **ambiguous_prefix** | **вместо** commit script — две ветки T9 |
| **ortho** | **после** T9 — Capitalize / sentence_case на surface |
| **listen** (ADR-0004) | **до или параллельно** — B1 cue может подсказать anchors |
| **hub** | **после** focus — соседи entity на L3 |

T9 **не** выбирает script; получает уже нормализованный prefix string.

### 8. Что **не** T9

| Подход | Почему вне scope |
|--------|------------------|
| `claims_nav` grep по markdown KB | RAG, не поле |
| Один JSON `hypothesis` без anchors | ломает multi-candidate UX и UC |
| Neural LM autocomplete | вне critic/extract petли v0 |
| B0 grapheme predict | modality `script` / listen, не `t9` |
| Phone keypad 2-9 mapping | лишний слой; Unicode prefix достаточен |

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Сразу F0 compose (cow+cow) | непонятный demo; слова — тот же predict loop |
| Top-1 only API | теряется ambiguity (`ма` → мама|майка|…) |
| Ingest «completion rules» | prescribe; не emergent field |
| T9 на L3 без B2 | пропуск слоя; context mode только **поверх** стабильного L2 |

---

## Lab status (2026-05-30)

| Artifact | Статус |
|----------|--------|
| `predict_t9` / `predict_tick` | **есть** |
| `bench_t9_predict.py` | **есть** |
| `bench_t9_lexicon_sweep.py` | **есть** |
| `bench_en_t9_smoke.py` | **есть** (EN store) |
| `lab/exp_t9/t9_manual_cues.v1.json` | **есть** |
| `unified_tick` + bench | **есть** |
| `run_t9_demo_cycle` + `t9_runtime` + C# console | **есть** |
| context L3 (`согласно пр` → `приказу`) | **нет bench** |
| `t9_segment_cues` / segment as T9 | **нет** — use `segment` modality |

---

## Verification

- [x] prefix `мам` → `мама` in anchors / top-1
- [x] ambiguous `ма` → `expect_in` pass via critic
- [x] `simulate_t9_type("мама")` — letter loop green
- [x] unified: script → T9 на bilingual prefix
- [ ] context cue L3 + `R:` dative — roadmap
- [x] `claims_nav_enabled=false` на bench

---

## Открытые вопросы

| # | Вопрос | Draft |
|---|--------|-------|
| Q1 | Минимальная длина prefix для rank? | `min_prefix=1` в sweep; critic требует ≥2 anchors на коротком |
| Q2 | EN/RU в одном tick? | unified dual branch; **layout parity** — [`CASA-ADR-0008`](CASA-ADR-0008-layout-parity-bilingual-t9.md) |
| Q3 | Hub до или после focus? | после — hub на resolved word |
| Q4 | Context T9 = отдельная modality или `t9` + `context` arg? | один `predict_t9`, опциональный L3 prior (roadmap) |

---

## Связанные ADR / docs

- **ADR-0003** — anchors, emergent Form, predictor не пишет LTM.
- **ADR-0004** — listen B1 может сужать T9 anchors (macro).
- **ADR-0005** — write W2 **после** T9 word known (dictation macro).
- **ADR-0008** — layout-parity bilingual T9 (PhysicalKeyEvent, без WinAPI в core).
- [`experiment-t9-predictive-words.md`](experiment-t9-predictive-words.md) — cues, metrics, smoke commands.
- [`predictor.md`](predictor.md) — полный контракт Predictor (T9 — один из modalities).
