# CASA-ADR-0005: write-модальность — письмо буквы (motor / compose)

**Статус:** draft (обсуждение, 2026-05-30)  
**Область:** ССС / букварь / motor / babble / grapheme production  
**Связано:** [`CASA-ADR-0004-listen-modality-bukvar-sound.md`](CASA-ADR-0004-listen-modality-bukvar-sound.md), [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md), [`bukvar-text-modality-v0.md`](bukvar-text-modality-v0.md), [`second-signal-system-v0.md`](second-signal-system-v0.md)

---

## Контекст

### Слушать и видеть — есть; **писать** — нет

Lab v0 покрывает:

| Вход | Lab |
|------|-----|
| grapheme L0, script, homoglyph | `grapheme_*`, `script_*` |
| слово L2, T9 | `predict_t9`, `unified_tick` |
| cursive **reference** PNG | ScriptS → `grapheme-glyphs/` |
| listen (draft) | ADR-0004 |

**Продукция знака** (рука, мышь, лепет на поле) — в design как **babble B0**, в hot path почти не развернута.

### Руки нет — что есть

| Actuator v0 | Что измеряем |
|-------------|--------------|
| **Мышь** | polyline stroke, drag path, click-sequence на canvas |
| **Grid babble** | размещение `G:` / stroke-token на L0 lattice (внутренний «черновик») |
| **Compose из элементов** | Process: `stroke.*` → `grapheme.*` (как `Capitalize` → surface) |

Рука — roadmap; **motor particular** можно episodic сохранять уже сейчас (`T:motor_trace`, `E: trace | instantiates | grapheme.cyrl.м`).

### Пара listen ↔ write

```text
  LISTEN (ADR-0004)              WRITE (этот ADR)
  ─────────────────              ────────────────
  cue: звук / слог               cue: «напиши м»
  predict: word anchors          act: stroke / grid compose
  critic: teacher heard          critic: shape vs reference
  extract: syllable→word        extract: stroke→grapheme Form
```

---

## Решение (draft)

### 1. Два режима write (не смешивать)

| Режим | Суть | Lab |
|-------|------|-----|
| **Motor-external** | мышь рисует на canvas; trace → critic | UI / recorded polyline |
| **Motor-internal** | babble: compose grapheme из **элементов** на grid | без UI; чистый digest |

Оба сходятся на **одном critic**: «получилась ли **Form** буквы `м`?», не «красиво ли SVG».

### 2. Элементы буквы (не SVG-font в ingest)

Bootstrap **не** кладёт «как рисовать м» JSON. Допустимо:

```text
stroke.arc.small     — primitive (particular)
stroke.down.long
  │
  └── Process compose (emergent / extract):
        Write(grapheme) ≡ fold(strokes)   ← аналог Upper ≡ fold(Capitalize)
```

**Reference** для critic v0:

- PNG из [`grapheme-glyphs/`](../lab/exp_bilingual_v0/grapheme-glyphs/) (ScriptS cursive)
- или упрощённый **prototype** на grid (occupancy mask L0 cell)

Teacher: human overlay «вот так», surprise → Extract mint `proc.stroke.*` или `E: stroke | part_of | grapheme`.

### 3. Mouse v0 contract

```text
  task: «напиши м» (cursive)
       │
       ▼
  PREDICT ──► target grapheme.cyrl.м + optional proc hints
       │
       ▼
  ACT ──► polyline[] / grid cells[]  (motor trace)
       │
       ▼
  CRITIC ──► overlap / DTW-lite / teacher accept
       │
  fail ▼
  EXTRACT ──► stroke primitive или порядок штрихов на L3
```

**Не** требуем pressure/velocity v0 — только `(x,y,t)*` или rasterized mask.

Critic **не** CV-neural oracle в bootstrap: rubric (IoU с mask, Hausdorff threshold) + **teacher click** «да/нет».

### 4. Compose-from-elements (без мыши)

Когда рук нет — агент **пробует собрать** букву на L0:

```text
  babble: place stroke tokens on grid
       │
       ▼
  decode → похоже на grapheme.cyrl.м?
       │
       ▼
  critic vs ScriptS PNG hash / grid template
```

Это **тот же write modality**, actuator = internal NCA/grid, не pointer.

Связь с ortho (ADR-0003): ortho = **какой Unicode surface**; write = **как нарисовать Form** particular.

### 5. Лестница write — как у ребёнка (не только «буква сразу»)

Педагогический порядок **не** совпадает с «сразу grapheme token». Сначала — **куча элементов**, потом буквы, слова, строки; **свой почерк** — в конце, emergent.

```text
  W-1  элементы штриха     дуги, палочки, петли — «каллиграфический лепет»
   │   critic: effort / teacher «продолжай», не «это м»
   ▼
  W0   буква целиком        одна grapheme Form vs эталон (ScriptS / grid)
   ▼
  W1   слог / пара букв     spacing, join, порядок штрихов
   ▼
  W2   слово                L2 lexeme, baseline внутри слова
   ▼
  W3   предложение           B3: слова + пробел + пунктуация + line layout
   ▼
  W*   почерк (particular)   отклонение от учебника — **свой** motor Form, не fail
```

| Ступень | Что пишет | Critic | concept / layer |
|---------|-----------|--------|-----------------|
| **W-1** | stroke primitives, «каракули» | loose; teacher не требует букву | `stroke.*`, motor episodic |
| **W0** | одна буква | shape IoU vs reference | `grapheme.*` L0 |
| **W1** | слог как цепочка букв | sequence + join | `syllable.*` |
| **W2** | слово | L2 + per-glyph | `lang.word.*` |
| **W3** | **предложение** | B3 layout: word order, space, `.?!`, baseline | `phrase.*` / `ru.dialog.*` L3 |
| **W\*** | **свой почерк** | identity match **своим** traces, не ScriptS | `form.write.hand.*` emergent |

**W-1 обязателен:** lab не должен требовать «напиши м» до того, как агент **сыпал** элементами и получил positive critic на motor babble (как B0 listen до babble grapheme).

**Почерк (W\*):** ScriptS / пропись — **teacher reference** на ранних W0–W2; после накопления motor traces critic смещается: «похоже на **твои** прошлые `м`», не на канон. Это **Form particular** (ADR-0003), не tag `handwriting: cursive` в ingest.

### 5b. B3 «предложения» — design есть, hot path **нет**

В цилиндре уже намечено:

| Есть в design / infra | Нет в lab v0 |
|----------------------|--------------|
| `L3_phrase` lattice, `ru.dialog.*` | `phrase_tick` / bench sentence compose |
| `ortho` `sentence_case`, `proc.word.sentence_case` | predict **целое предложение** по prefix |
| entity hub на L3 | write **строку** (W3) |
| realize v0 — шаблоны фраз | listen **фразу** end-to-end (ADR-0004) |
| UC: paraphrase / scene H3 | unified tick до B3 |

**Gap:** мы разогнали B0–B2 (grapheme, T9 word, script, ortho surface), но **предложение как единица** — ни read, ни write, ни listen macro. B3 в таблице букваря — **контракт**, не пройденный bench.

Roadmap B3 (draft):

```text
  phrase_ingest / scene cue  →  L3_phrase activation
  predict_phrase_v0          →  word sequence + punctuation anchors
  write W3                   →  line layout critic
  listen B3                  →  «услышал фразу» → L3 (после B1/B2 стабильны)
```

Не перескакивать на «напиши мама» (W2) без W-1/W0; не на «напиши предложение» (W3) без стабильного W2 **и** L3 phrase layer в store.

### 5c. Зеркало listen ↔ write (полная лестница)

| Ступень | Listen | Write |
|---------|--------|-------|
| элемент / лепет | звук буквы, шум | W-1 strokes |
| B0 | grapheme anchor | W0 letter |
| B1 | слог | W1 syllable chain |
| B2 | слово | W2 word |
| B3 | **фраза** (gap) | **W3 sentence** (gap) |
| emergent | accent, tempo | **W\* handwriting** |

Старый §5 «лестница write» сжат в таблицу выше; порядок **W-1 → W0 → … → W3 → W\*** каноничен.

### 6. Первая vs вторая сигнальность

| | Первая СС (motor) | Вторая СС (sign) |
|---|-------------------|------------------|
| Носитель | trace, gesture, effort | `grapheme.*`, `lang.word.*` |
| Связь | `E: motor_trace \| instantiates \| grapheme` | знак **указывает** на образ (hub, позже) |

Motor trace — **не** дублирует grapheme token; **particular реализации** Form буквы.

### 7. Teacher contract

| Источник | Роль |
|----------|------|
| ScriptS PNG / grid template | **reference** для critic (как учебник прописи) |
| Human «покажи как» | episodic trace overlay → extract |
| Авто-IoU rubric | lab bench only, порог настраиваемый |
| TTS | **не** участвует |

### 8. Unified tick (roadmap)

```text
  listen? → script? → T9 word → ortho surface → write?(copy dictation)
```

T9 (prefix → anchors → focus): [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md).

Dictation: услышал `мама` → write letters — **multi-modality macro**, не один JSON.

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|-------------------|
| SVG paths в ingest | prescribe; не «научился писать» |
| End-to-end diffusion «нарисуй букву» | вне UC; нет critic/extract |
| Только мышь без internal compose | нет lab без UI |
| Только grid без mouse | нет проверки «как ребёнок рукой» |

---

## Lab phases (предлагаемые)

| Фаза | Ступень | Что | Bench |
|------|---------|-----|-------|
| W-1 | элементы | motor babble strokes, loose critic | teacher / coverage |
| W0 | буква | grid compose → mask vs ScriptS PNG | IoU ≥ threshold |
| W1 | слог | letter chain + spacing | sequence |
| W2 | слово | per-glyph line | L2 match |
| W3 | **предложение** | line + punctuation layout | **нет lab** |
| W\* | почерк | critic vs own traces | emergent Form |
| W1m | mouse | trace record/replay | teacher accept |
| W2x | stroke Extract | fail → `proc.stroke.*` on L3 | extract lab |
| macro | dictation | listen + write word | unified (после ADR-0004) |

---

## Открытые вопросы

| # | Вопрос | Draft |
|---|--------|-------|
| Q1 | Stroke primitives в bootstrap или только Extract? | только **Capitalize-level** atom 1–2; остальное Extract |
| Q2 | Один canvas на все буквы vs grid cell? | grid aligned с L0 lattice |
| Q3 | Cursive ScriptS vs print grapheme — разные write Forms? | да, `form.write.cursive` vs `form.write.print` (emergent) |
| Q5 | W-1 без целевой буквы — что в cues? | «рисуй», teacher accept any stroke set |
| Q6 | Почерк vs эталон — когда переключать critic? | после K успешных W0 **и** teacher «можешь по-своему» |

---

## Verification (когда lab)

- [ ] B0 write «м» internal compose → critic pass vs ScriptS mask
- [ ] Fail trace → Extract mints stroke edge
- [ ] Write **не** путает latn `m` и cyrl `м` basins (separate templates)
- [ ] Unified: hear `ма` → write `ма` (sequence)

---

## Связанные ADR

- **ADR-0004** — listen (вход); **0005** — write (выход).
- **ADR-0003** — Process compose, Form не tag.
- **grapheme-glyphs** — visual reference для critic write.
