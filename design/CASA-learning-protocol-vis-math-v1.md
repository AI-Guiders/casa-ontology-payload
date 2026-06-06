# Learning-protocol: vis↔math (von-neumann / visual-cards)

**Статус:** канон lab + teacher inbox  
**Дата:** 2026-06-02  
**Область:** как **учить** агента считать по картинкам — педагогика, не ML-bench  
**Связано:**

- [CASA-ADR-0021-experience-agent-transfer.md](CASA-ADR-0021-experience-agent-transfer.md) — опыт на поле, без oracle на read
- [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md) — тракт `visual`, predict `modality=vis`
- [CASA-ADR-0037-gate-zun-verification.md](CASA-ADR-0037-gate-zun-verification.md) — gate = проверка ЗУН (META)
- [`CASA-literacy-class-v1.md`](CASA-literacy-class-v1.md) — vis↔lex, метаязык (дополнение ниже)
- [`CASA-visual-3D-tract-future.md`](CASA-visual-3D-tract-future.md) — черновик: lum v1 → depth v2 → spherical v3 (не канон lab v1)
- `casa/cli/ingest_lesson_moment.py` — lesson moment (visual + math → один sleep)
- `casa/prisms/visual/bridge_math.py` — emergent bridges, `predict_math_for_vis_cue`
- `tools/teacher_count_session.py` — teacher: закрепление → квиз «посчитай»

---

## Принцип (одной фразой)

**Подбор подхода — работа обучающего, не обучаемого.** Ошибка на доске — диагностика для учителя, не повод лезть в веса, ставить guardrails или «обнулить экзамен».

---

## Мосты — его, не наши

Агент **сам** создаёт vis↔math связи — какие посчитает нужными:

- **Sleep co-occurrence** — первый раз, когда vis и math были в одном batch
- **`self_promote` / hypothesis** — сам заметил нестыковку, записал в `entries.jsonl`, mint через Kolb
- **`agent_promote_crosslink`** — осознанное решение агента, не учителя

**Учитель даёт среду:** картинка, число рядом, другие слова, другой порядок, другой контекст (зёрна vs коровы).  
**Учитель не перепрошивает мозг:** не усиливает мосты снаружи, не чинит probe, не подкручивает ranker, не «reinforce» повторный co-occurrence в коде.

Если на квизе «не понял» — **не понял**. Повторить урок **другими словами/картинками**. Ждать, пока **он** вырастит или пересмотрит связь. Память von-neumann — его биография, не баг для hotfix.

---

## Роли

| Роль | Делает | Не делает |
|------|--------|-----------|
| **Учитель** (inbox / CLI moment) | Показывает картинку, называет число **рядом**, даёт закрепление, задаёт held-out «посчитай» | Не подсказывает ответ через manifest на predict; не штрафует gradient clip; **не лезет в mint/reinforce** |
| **Агент** (von-neumann) | Импринт LRGB, episodic math, sleep, **свои** emergent / self_promote мосты | Не обязан угадывать форму онтологии дизайнера |
| **Probe** | `predict_math_for_vis_cue(state, frame_id)` — что **само** на поле | Gate **З/Н** на held-out ([ADR-0037](CASA-ADR-0037-gate-zun-verification.md)); hint в отчёте — не substitute predict |

---

## Фазы curriculum

### 1. Lesson moment (основной путь)

Один **момент урока** = чередование visual imprint + math episodic → **один sleep**.

```text
  [visual frame] → [math cue + concept_id] → … → sleep → emergent bridges (если агент/sleep так решили)
```

- CLI: `ingest_lesson_moment`, план: `moment_plan.build_moment_steps`
- Batch: `tools/run_visual_moment_curriculum.py`
- Inbox: `kind: "lesson_moment"`

### 2. Закрепление (reinforcement)

Тот же формат — **ещё один урок**, не патч движка. Другие слова, другие картинки, тот же смысл.

Пример: `teacher-reinforce-count`, `--lesson orion-invariant-two` (зёрна + коровы + «два»).

### 3. Квиз «посчитай» (held-out)

Probe по `frame_id` — что на поле **сейчас**. Отчёт для учителя, не verdict для gradient descent.

### 4. Множества (Эйлера–Венна)

`stage-13-sets` / `lesson-13-sets` — два круга A и B: пересечение, объединение, подмножество, «только A».  
Teacher moment: картинка → число или символ множества (`∩`, `∪`, `⊂`) **рядом**; мосты — **его** (sleep / self_promote).

Картинки: `lessons/visual-cards/tools/build_card_images.py` → `lesson-13-sets/images/`.

---

## Семантическое именование `concept_id` (канон)

**Правило:** id в онтологии — **английский semantic slug**, не транслит русской поверхности. На JPEG и в `correct` — **кириллица** (или glyph). `frame_id` / slug кадра — латиница для путей (`word-size-large-sans`), не `bolshaya`, не `zaglavnaya_bukva`.

| Префикс | Назначение | Пример |
|---------|------------|--------|
| `grapheme.{locale}.{cue}.{register}` | буква как знак | `grapheme.cyrl.b.upper` |
| `lang.word.{semantic}` | цельное слово корпуса / legacy мета-слово | `lang.word.mama`, `lang.word.ne_znayu` (→ миграция) |
| **`lang.meta.{category}`** | **домен метаязыка** (ось учителя) | `lang.meta.size`, `lang.meta.register`, `lang.meta.epistemic` |
| **`lang.meta.{category}.{facet}`** | конкретная метка в домене | `lang.meta.size.large`, `lang.meta.letterCase.upper` |

**Категория vs facet:** домен `size` — ось «размер»; facets `large` / `small` — отдельные concept на карточках «большая» / «маленькая». Два синонима **одного** facet (как «заглавная буква» и «буква верхнего регистра») → **один** `concept_id`, два frame/surface.

**Одна категория — много выражений (язык, длина фразы):** мета может звучать и выглядеть на тексте по-разному; **инвариант для поля и probe — `concept_id`**, не конкретная строка и не язык.

| Слой | Меняется между подачами? | Пример |
|------|--------------------------|--------|
| **`concept_id`** | **Нет** (канон) | `lang.meta.size.comparative.greater` |
| **surface / `correct`** | Да | RU: «Этот круг больше других»; EN: «This circle is bigger than the others» |
| **`lattice_id`** | Да (локаль) | `lexicon-ru` vs `lexicon-en` — тот же id, другой лексический пакет |
| **vis / episodic** | Да (контекст) | большой круг среди маленьких; та же категория, другой кадр |

Не заводить отдельный `concept_id` под каждую формулировку, язык или длину фразы. Разные moment’ы с **одним** id учат один мост; probe с hint по **id** — «знаю категорию», не «знаю только эту цитату».

Отличие facet’ов внутри домена `size`: **`lang.meta.size.large`** — метка «большой/большая» (прилагательное на карточке); **`lang.meta.size.comparative.greater`** — сравнение «больше (других/остальных)» на vis+фразе. Это разные concept, не RU vs EN одного и того же.

**Переименование без переучивания:** маршрут тот же (`lexicon-ru`), меняются только строки id в snapshot. Один раз: `python tools/migrate_lex_concept_store.py` (таблица `LEX_CONCEPT_RENAMES` в `meta_concept_aliases.py`). После миграции в store **нет** legacy id — probe/manifest только канон (`lang.meta.letterCase.upper`, …). До миграции read path нормализует legacy → canon в `predict` (не дублирует лидеров).

Канон: `meta_concept_aliases.py`; карточки: `lessons/literacy-cards/tools/meta_concepts.py`.

**Не использовать:** транслит поверхности в id (`bolshaya`, `ne_znayu` в новых доменах — только legacy до pure re-ingest).

---

## Vis↔lex: метаязык **отдельно** (lab 2026-06-03)

Ось **vis↔lex** — общая для visual-curriculum (`literacy-cards`, `visual-cards`, …), не свойство только literacy. Lab: `lab/visual-curriculum/curriculum_lab.py`, `lex_steps.py`; отчёты по подклассу — `generated/micro-literacy`, `generated/micro-geom`, … (не в git)

Тот же принцип, что vis↔math: **мосты его**, учитель меняет **подачу**, не `bridge_lex` / sleep снаружи.

**Вывод дня:** мета-слова (`lang.word.*` на карточке-фразе) и **гранулярность** (`grapheme.*`, категория регистра на кадре буквы) — **разные уроки**. Смешивать в одном moment / одном sleep (буква + «заглавная буква» + «А») даёт cartesian co-occurrence и probe **ambiguous** — это «не знаю» по протоколу, не miss для hotfix.

| Подача | Probe (пример lab) | Смысл |
|--------|-------------------|--------|
| **Чистый мета-moment** — только фраза или `phrase_vis` (1 vis + 1 lex), **без** `letter-*` | `word-capital-*` → **know** `capital_letter`; `word-ne_znayu-sans` → **know** `ne_znayu` | метка на **своём** JPEG читается с поля |
| **Exemplar** — `letter-Б` + фразы категории в одном sleep | `letter-b-upper` + hint `capital_letter` → **ambiguous** (grapheme + категория) | категория **рядом** с буквой, не вместо |
| **Guided** vis буквы + метаслово + grapheme (старый путь) | часто шум, особенно **а/А** | не использовать как **единственный** путь метаязыка |

**Правило curriculum (канон):**

1. Сначала **чистые** moment’ы на карточку меты (`run_register_category_pure.py`, `run_meta_ne_znayu_pure.py`, …).
2. Потом — контрасты **grapheme** (регистр, upper-only, cue Б/В без **а** в начале).
3. Категорию регистра на букве — exemplar **не на а**; фразы категории — отдельно от grapheme в batch.
4. **«Не знаю» как состояние** (связь с ambiguous на букве) — **не** уровень 1; отдельный guided-трек позже.

**Compare (больше / меньше):** канон — [CASA-compare-greater-less-v1.md](CASA-compare-greater-less-v1.md): `math.compare` на прямой → `lang.meta.compare.greater` / `.less` → два круга; **центр и радиус после compare**, не до.

**Размер-прилагательное (большая / маленькая):** w2 на текстовых карточках → `lang.meta.size.large` / `.small` (отдельно от compare). Lab «один большой / один маленький круг» — **снят** (ambiguous без отношения).

Подробности: [CASA-literacy-class-v1.md](CASA-literacy-class-v1.md) § Метаязык; compare: [CASA-compare-greater-less-v1.md](CASA-compare-greater-less-v1.md).

**Грамматика, формы, согласование (канон):** [CASA-ADR-0036-emergent-morph-agreement.md](CASA-ADR-0036-emergent-morph-agreement.md). **Gate (шаг 5):** [CASA-ADR-0037-gate-zun-verification.md](CASA-ADR-0037-gate-zun-verification.md) — проверка ЗУН на held-out; sidecar `phrase_*` v0 без store — не gate.

---

## Что считать успехом

| Сигнал | Значение |
|--------|----------|
| `kind: hypothesis` в `entries.jsonl` | инициатива — сам увидел gap |
| Агент сам mint `self_promote` vis↔math | связь **его**, не oracle |
| Квиз: единственный лидер по score = teacher hint | **знаю** (know) |
| Квиз: равный max score у нескольких concept | **не знаю** (ambiguous), не ошибка |
| Квиз: единственный лидер ≠ hint | miss → **учитель меняет подачу**, не код |

---

## Анти-patterns (изверги)

- Manifest oracle на predict
- Gradient clip / guardrails / принудительный reinforce мостов в `mint_crosslink`
- Обнулить store ради красивого pass (см. ниже)
- Автоматический цикл «крути пока score не вырос» — это optimization, не pedagogy

---

## Чистый store — жульничество или нет?

| Сценарий | Честно? |
|----------|---------|
| Wipe von-neumann и «пересдать» held-out | **Жульничество** |
| Новый агент для изолированного lab-эксперимента (явный `store_id`, `run_tag`) | **Честно** |
| Учить **того же** von-neumann: повтор moment, другой контекст | **Честно и предпочтительно** |

---

## Операционные правила

1. Один writer на store — `store_session_lock`
2. Reentrant persist — не deadlock при session lock (инфраструктура, не pedagogy)
3. Отчёт в `lab/visual-curriculum/generated/` **до** persist

---

## Команды (шпаргалка)

```bash
# Закрепление + квиз
python tools/teacher_count_session.py

# Orion: зёрна + коровы + «два» — ещё раз урок, не патч
python tools/teacher_count_session.py --lesson orion-invariant-two

# Только «посчитай», без нового moment
python tools/teacher_count_session.py --skip-reinforce

# Множества (Venn) — один stage как lesson moment
python -m casa.cli.ingest_lesson_moment --stage stage-13-sets
```

**Пока «два» не вытянется:** повторять moment (можно тот же CLI несколько раз), смотреть probe, менять **подачу** — не код.

---

*«Не понял — значит не понял. Повторить по-другому. Не перепрошивать.»*
