# CASA-ADR-0003: emergent Forms, tags и граница Predictor

**Статус:** принято (design, 2026-05-30)  
**Область:** SSS / bilingual / букварь / predictive cognition  
**Связано:** [`understanding-contract-v0.md`](understanding-contract-v0.md), [`predictor-v0.md`](predictor-v0.md), [`experiment-bilingual-entity-v0.md`](experiment-bilingual-entity-v0.md), [`bukvar-text-modality-v0.md`](bukvar-text-modality-v0.md), [`CASA-ADR-0004-listen-modality-bukvar-sound.md`](CASA-ADR-0004-listen-modality-bukvar-sound.md), [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)

---

## Контекст

### Проблема «тегов сверху»

При проектировании EN/RU lab естественно ввести ярлыки вроде `#Letter`, `#Latin`, `#Cyrillic`, `#Uppercase` — чтобы не спутать Latin **B** (Bob) и Cyrillic **В** (вагон).

Если записать их в ingest как `slots.tags: [...]` или зашить в `concept_id`, получится **онтология дизайнера**, а не знание агента — тот же класс ошибки, что § grammar в KB вместо `R:` на поле после Extract.

### Платоновская «идея» в инженерном смысле

В диалоге всплыла метафора **идеи (Form)** vs **частного (particular)**:

| Метафора | CASA (не метафизика) |
|----------|----------------------|
| Идея «корова» | hub `entity.cow` — то, что связывает `cow` и `корова` |
| Идея «латинская b» | устойчивый кластер знаков + позже имя `form.letter.latn_b` (roadmap) |
| Частное | `W:cow`, `W:корова`, glyph `b`/`B` в контексте |
| Участие в идее | `E:lang.word.cow\|denotes\|entity.cow`, co-activation с hub |

**ADR не утверждает** философский платонизм. Фиксируется **инженерный контракт**: *Form* = **устойчивый hub / attractor на поле**, имя которого (`entity.*`, `form.*`, `meta.tag.*`) появляется **после** стабилизации опыта, не в bootstrap.

### Predictor — это «генератор идей»?

Частично да, частично нет:

| Модуль | Что делает с «идеями» |
|--------|------------------------|
| **Predictor** | при partial cue **активирует конкурирующие якоря** уже на поле (`anchors[]`) |
| **Babble / compose** | **синтезирует** черновик из digest (лепет, compose-up L0→L2) |
| **Critic** | сравнивает ожидание с наблюдением |
| **Extract → Remember** | при surprise **кристаллизует** новую структуру (`R:`, `E:`, hub) |
| **Sleep / consolidate** | укрепляет Form, повышает точность следующего Predict |

**Predictor** — генератор **гипотез-активаций** ( «что из уже имеющегося может подойти?» ), не минтер **новых** Forms.  
**Extract** (после Critic) — контур **рождения/именования** Form.

---

## Решение

### 1. Три слоя знака (не смешивать)

```text
  Particular (частное)     Form (идея / hub)           Meta-name (ярлык для нас/учителя)
  ─────────────────────    ───────────────────         ────────────────────────────────
  W:cow, glyph b, B        entity.cow                  (описание в design doc)
  lang.word.the            form.letter.latn_b (v1+)    meta.tag.Latin (v1+, emergent)
  co-occurrence на L0/L2   meta.tag.* на L3 (v1+)      #Letter — не поле ingest
```

**Ingest v0 кладёт только Particular + co-occurrence** (токены на L0/L2/L3).  
**Form** и **tag** — результат цикла listen → babble → correct → Extract → sleep.

### 2. Emergent tags — что это в поле

*Tag* — не JSON-property при рождении, а **именованный класс устойчивого поведения** кластера:

| Tag (design vocabulary) | Как выводится (не prescribe) |
|-------------------------|------------------------------|
| `#Letter` vs `#Word` | знак стабильно **внутри** compose `c-o-w` vs активируется **целиком** как `lang.word.the` |
| `#Latin` / `#Cyrillic` | два **разделяющихся basins** co-activation: кластер A с `L2_en_word_*`, кластер B с `L2_word_*` |
| `#Uppercase` | класс episodic correct: тот же lexeme, другой glyph в контексте (начало фразы, имя) → `R:en.ortho.*` |
| confusable B / В | **не** `align`; ошибка смешения + correction → разные subgraph, опционально `E:*\|visually_confusable\|*` |

Bench v1 для tags: **разделимость кластеров**, не «есть ли ключ `tags` в manifest».

### 3. Script namespace в ingest (сигнал, не tag)

Для lab bootstrap допустим **namespace в `concept_id`**, чтобы не merge'ить basins на диске:

```text
grapheme.latn.c   — particular на EN store L0
grapheme.cyrl.ve  — particular на RU store L0
```

Это **не** tag `#Latin` в hot path. Это **разнесение опыта** (отдельные store / lattice basins), из которого агент *может* вывести «два алфавита». Design-doc может писать `#Latin`; ingest — только `grapheme.latn.*`.

### 4. Разделение модулей predictive cognition

```text
  cue (partial)
       │
       ▼
  PREDICTOR ──► AnchorActivation[]   ← конкуренция уже существующих якорей
       │
       ▼
  CRITIC ──► pass | surprise
       │
   surprise
       │
       ▼
  EXTRACT ──► новые E:, R:, hub (Form crystallize)
       │
       ▼
  REMEMBER / sleep ──► ltm + hippo; Form устойчивее
       │
       ▼
  следующий PREDICTOR точнее активирует тот же Form
```

| Имя | Роль | Аналог в UC |
|-----|------|-------------|
| **Predictor** | «что может быть?» — `anchors[]`, не singleton | UC v0.5–v0.6 |
| **Babble** | низкоуровневый синтез из digest | CEN / compose |
| **Critic** | validate expectation | UC v0.6 |
| **Extract** | **минтер Form** при mismatch | hippo H1/H2/H3 |
| **Name** (опционально, v1+) | teacher/meta label для стабильного кластера → `meta.tag.*` | cold path |

**Не вводим** отдельный модуль «IdeaGenerator» на hot path: это **роль Extract + sleep**, Predictor остаётся **retrieval/simulation over existing field**.

### 5. Связь с entity hub (bilingual)

Паттерн ADR-0003 **совпадает** с [`experiment-bilingual-entity-v0.md`](experiment-bilingual-entity-v0.md):

```text
  entity.cow  ← Form
  lang.word.cow, lang.word.корова  ← particulars
  E:denotes  ← participation
```

`entity.cow` не «спускается» как перевод; hub **вырастает** из co-occurrence + correction.  
Tags по script — **тот же hub-паттерн** на уровне букв: два basins, не word=word align.

**Homoglyph vs confusable (lab v0):**

| Тип | Пример | Lab |
|-----|--------|-----|
| Homoglyph (один glyph, два code point) | `a/а`, `c/с`, `e/е`, `o/о`, `p/р`, `x/х`, `y/у` | `homoglyph_v0` → dual read |
| Confusable (разный glyph, cross-talk) | `b` vs `в`, `n` vs `н`, `B` vs `В` | `grapheme_clusters` cross-talk bench |

**Commit vs pre-commit:** `script_detect` — язык уже выбран (unambiguous cue). `ambiguous_prefix` — `co` → cow | сова, пока буква не отсечёт ветку (`w` → EN; RU — кириллица `сов`).

### 6. Uppercase без 52 grapheme

Заглавная — **surface transform** в контексте, не вторая буква алфавита:

```text
grapheme.latn.b  (Form буквы, lowercase как canonical particular)
       │
       └── E:grapheme.latn.b|glyph.upper|B   ← edge после Extract, не bootstrap tag
```

Canonical lexeme на L2: `lang.word.cow` через `norm_word`. Ortho `Cow` — L-surface / `R:en.ortho.*`.

### 7. Process — операции над grapheme и словом (roadmap)

**Tag** отвечает «к **классу** относится знак». **Form** — «**что** это за единый смысл». **Process** — «**что можно сделать** с particular, не меняя Form».

#### 7.1 Атом и композиция (канон)

**Один атом на L0** — `Capitalize(grapheme)`: lower glyph → upper glyph (`м→М`, `b→B`).

**Слово — fold по буквам** (compose-up L0→L2):

```text
Upper(word) ≡ for letter in word: Capitalize(letter)

  Upper("мама") → "МАМА"
```

`Upper` не второй примитив — **свернутый** `Capitalize`. На поле: `P:proc.grapheme.capitalize`, `P:proc.word.upper`, `E:proc.word.upper|fold|proc.grapheme.capitalize`.

**Sentence case** («Мама»): `SentenceCase(word) ≡ Capitalize(first(letter)) · Id(rest)`. Rule (`R:`) выбирает compose по контексту.

**«мама» и «МАМА» — одно слово:** canonical на L2 = `lang.word.мама` (`norm_word` → lower).  
Caps — **ortho surface**, не второй headword. Critic сравнивает через `norm_word`; Predict/Act **применяет** Process для **отображения**, не для идентичности.

| Surface | Compose |
|---------|---------|
| `мама` | `Id(word)` |
| `Мама` | `SentenceCase(word)` |
| `МАМА` | `Upper(word)` |

Critic: `norm_word(surface) == norm_word(canonical)`; ortho-bench — верный compose в контексте.

**Токены (v1+):** `P:proc.grapheme.capitalize`, `P:proc.word.upper`, `P:proc.word.sentence_case`, `R:en.ortho.sentence_start`.

Отличие **Process** от **Rule (`R:`)**:

| | Process (`P:` / `proc.*`) | Rule (`R:`) |
|---|---------------------------|-------------|
| Суть | **что** (Capitalize, fold → Upper) | **когда** / контекст |
| Пример | `Upper` = map Capitalize | «начало предложения» → SentenceCase |
| Вывод | Extract после «сделай большую букву» | Extract после «здесь начало предложения» |

Оба **emergent** — не в ingest tags; учатся из episodic correct.

**Petля (lab v0 — `ortho_tick_v0.py`):**

```text
  cue + context
       │
       ▼
  PREDICT ──► lexeme + expect_display (plain → lowercase surface)
       │
       ▼
  ACT (naive) ──► only Upper learned → wrongly Upper in plain
       │
       ▼
  CRITIC ──► lexeme_ok, display fail
       │
  mismatch ▼
  EXTRACT (auto in ortho_tick) ──► proc.grapheme.lower + proc.word.lower
       │
       ▼
  ACT (naive) ──► sees МАМА vs мама → inverse Lower from field
```

Инструмент: `bench_ortho_inverse_v0.py` — hot-path через `simulate_ortho_plain_surprise`, **без** явного `extract_inverse_after_surprise()` в bench.

**Связь с Predictor:** Predictor активирует **и** lexeme, **и** (когда выучено) applicable `P:` / `R:` в контексте — «что будет, если применить capitalize здесь». Это не отдельный IdeaGenerator; Apply = compose/babble под digest с Process-токенами.

**Bench v2:** `Upper("мама")`→`МАМА`; `SentenceCase("мама")`→`Мама`; norm identity для всех.

#### 7.5 Inverse / Lower (emergent, lab v0)

```text
Lower(grapheme)  — inverse Capitalize (м ← М)
Lower(word)      ≡ map Lower  ≡ inverse Upper
```

**Не в bootstrap.** После surprise (plain context + `МАМА` вместо `мама`, `lexeme_ok`):

1. `derive_inverse_grapheme_proc`: на алфавите L0 проверить `lower(capitalize(ch))==ch`
2. Extract → `P:proc.grapheme.lower`, `E:capitalize|inverse|lower`, `proc.word.lower` + fold

Инструмент: `bench_ortho_inverse_v0.py` — **7/7** (Lower отсутствует → surprise → Extract → undo).

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| Tags в ingest JSON | RAG-онтология; агент не «понял», а прочитал property |
| 52 grapheme (a/A × 26) | дублирует Form/particular; uppercase = transform |
| Один flat `grapheme.b` для B и В | смешивает script basins; ломает bilingual |
| Predictor = единственный «мыслитель» | не создаёт новые hub при первом encounter |
| Отдельный IdeaGenerator LLM | внешний oracle; против UC «модель = grid + CA + decode» |

---

## Последствия

### Lab v0 (сейчас)

- EN folk store: L2 `lang.word.*`; L0 `grapheme.latn.*` derive из lexicon — **без** `tags[]`.
- Linked RU+EN: merge L2 namespaces; L0 merge **по script basins**, не по glyph similarity.
- Bench: T9 ([`CASA-ADR-0006`](CASA-ADR-0006-t9-predictive-text.md)), entity hub, cluster separation (roadmap).

### Roadmap v1

- `bench_grapheme_clusters_v0`: B-context vs В-context activation separation.
- Extract ortho rules после episodic correct.
- `meta.tag.*` / `form.letter.*` — **имена** после consolidate, optional teacher label.

### Roadmap v2 (Process)

- Атом `proc.grapheme.capitalize`; compose `proc.word.upper` = fold Capitalize по слову.
- `proc.word.sentence_case` = Capitalize(first) · Id(rest); Rule — когда какой compose.
- Critic: `norm_word(surface) == norm_word(canonical)`; bench ortho compose, не второй headword.

### Что не меняется

- Predictor API: `anchors[]`, `focus` после Critic ([`predictor-v0.md`](predictor-v0.md)).
- KB остаётся cold path; design `#Latin` — vocabulary для команды, не runtime field.

---

## Проверка (критерии)

- [ ] Ingest EN/RU grapheme **без** поля `tags` в bundle/ltm manifest.
- [ ] Linked boot: Latin B и Cyrillic В не в одном `concept_id`.
- [ ] Документирован predict vs extract в [`understanding-contract-v0.md`](understanding-contract-v0.md) (ссылка на ADR).
- [x] `bench_ortho_inverse_v0.py` — Lower emerges after surprise, not bootstrap.

---

## Решённые вопросы (2026-05-30)

### 1. Где живёт Form — L3 или отдельная полка?

**Решение: L3 hub (как `entity.*`), без `F_form` в v0–v1.**

| Вариант | Вердикт |
|---------|---------|
| **`entity.*` / `form.*` на `L3_phrase`** | **да** — тот же hub-механизм, что bilingual entity; `entity_hub_ingest`, `hub_neighbors`, bench уже есть |
| **`F_form` / meta-lattice** | **отложить** — новый z-уровень оправдан, когда L3 decode шумный (пересечение phrase/rule/entity/form) **измеримо** на bench |

Именование:

```text
entity.cow              — Form вещи (существное)
form.letter.latn_b      — Form буквы (roadmap; тот же L3, другой prefix)
meta.tag.latn           — Form класса / script basin (после consolidate)
```

Particulars остаются на своих полках: `grapheme.*` → L0, `lang.word.*` → L2.  
`F0_schema` — **первая сигнальная система** (math); не смешивать с Form букв (SSS).

**Критерий пересмотра:** если `decode(L3)` для hub-neighbors падает по F1 при добавлении `form.*` — тогда shard L3 или отдельная meta-lattice **v2**.

### 2. Teacher label («это латиница») — cold path или episodic?

**Решение: оба слоя, строго по порядку.**

```text
  1) кластеры уже разделились (co-activation basins)     ← без этого label = RAG
  2) episodic meta_label (hippo)                         ← учитель в петле correct
  3) sleep → E: cluster ↔ C:meta.tag.latn на L3         ← Extract крепит имя
  4) cold path (KB / design #Latin)                      ← только для команды и lab docs
```

| Слой | Роль |
|------|------|
| **Episodic `kind: meta_label`** | учитель **именует** уже различимый кластер после confusion (B vs В, EN stream vs RU stream) |
| **Cold path** | наш vocabulary в ADR/design; **не** ingest `tags: ["Latin"]` как истина |

Label **без** предшествующей separability — не обучение, а подсказка из KB.  
Label **после** separability — как дать имя `entity.cow` уже связанным surfaces.

### 3. Bench emergent tags — нужна ли строка `#Latin`?

**Решение: нет. v1 bench = separability кластеров, не string match на tag.**

| Метрика | Что проверяем |
|---------|----------------|
| **Basin purity** | cue из EN/Latn контекста → top activations на `L2_en_word_*` + latn L0; RU — на `L2_word_*` + cyrl L0 |
| **Cross-talk** | cue «Bob» не тянет cyrl-В basin; «Вагon» не тянет latn-B |
| **Confusable pair** | B/В: после N episodic correct cross-activation < ε |

Фаза v1.5 (опционально): после mock `meta_label` episodic — hub `meta.tag.latn` **достижим** из latn basin через `hub_neighbors`. Всё ещё без assert на `#Latin` в JSON.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-30 | Первая версия: emergent tags, Form/particular, Predictor ≠ Form minter |
| 2026-05-30 | § Решённые вопросы: L3 hub, meta_label episodic, bench separability |
| 2026-05-30 | §7 Process: capitalize/uppercase как операция; мама ≡ МАМА через norm |
| 2026-05-30 | §7.1 compose: Upper(word) = fold Capitalize(letter) |
