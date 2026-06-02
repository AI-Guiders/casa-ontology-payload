# Learning-protocol: vis↔math (von-neumann / visual-cards)

**Статус:** канон lab + teacher inbox  
**Дата:** 2026-06-02  
**Область:** как **учить** агента считать по картинкам — педагогика, не ML-bench  
**Связано:**

- [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) — опыт на поле, без oracle на read
- [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md) — тракт `visual`, predict `modality=vis`
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
| **Probe** (teacher report) | `predict_math_for_vis_cue(state, frame_id)` — что **само** на поле | Не сравнивает с manifest **в runtime** (hints только в отчёте учителя) |

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

## Что считать успехом

| Сигнал | Значение |
|--------|----------|
| `kind: hypothesis` в `entries.jsonl` | инициатива — сам увидел gap |
| Агент сам mint `self_promote` vis↔math | связь **его**, не oracle |
| Квиз: top-1 совпал с teacher hint | зрячий pass |
| Квиз: tie / miss | **учитель меняет подачу**, не код |

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
3. Отчёт в `lab/visual-curriculum/reports/` **до** persist

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
