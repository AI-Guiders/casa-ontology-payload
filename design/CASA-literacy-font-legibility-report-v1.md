# Отчёт: font legibility sweep (32×32, von-neumann)

**Дата прогонов:** 2026-06 (lab, store `von-neumann`)  
**Протокол:** [CASA-literacy-font-legibility-experiment-v1.md](CASA-literacy-font-legibility-experiment-v1.md)  
**Машинный артефакт:** `lab/visual-curriculum/generated/teacher-font-legibility-sweep.json`  
**Скрипт:** `lab/visual-curriculum/probe_font_legibility_sweep.py`

---

## 1. Резюме

Эксперимент проверял, **падает ли узнавание уже выученного слова** при уменьшении размера шрифта на перерисованной карточке (ephemeral imprint на сетке **32×32**, без записи в store).

**Главный вывод:** для слов с **устойчивым мостом** `vis.lum.frame.{frame_id}` → `lang.word.*` verdict **know** не обрывается при уменьшении pt вплоть до **4–8 pt** (кот, предыдущий). Это **не** означает, что 32×2 достаточно для «чтения с листа»: метрики `lum_ink_cells` показывают, что сенсорный след на малых pt часто **пустой**, а predict опирается на **память урока по frame_id**, а не на свежий визуальный паттерн.

Для слов **без моста** (большинство пилотных 8) sweep по pt **бесполезен** — везде **empty**. Для **мамы** доминирует **ambiguous** с `grapheme.cyrl.a.lower` на всех pt — лимит **конкуренции буквы «а»**, не шрифта.

**Практическая рекомендация:** порог «минимального pt для чтения» на этом probe **не калибруется**; сначала нужен чистый **know** на стандартном corpus probe, затем sweep. Для оценки сенсорики 32×2 смотреть **`lum_ink_cells` / `lum_bbox_*`**, не только verdict.

---

## 2. Вопрос и гипотезы

| # | Вопрос / гипотеза |
|---|-------------------|
| H1 | При малом PIL pt на 640×480 после `retinal_lrgb` слово перестаёт давать **know** на predict. |
| H2 | Падение **know_rate** коррелирует с ростом «пустого» следа (`lum_ink_cells` → 0). |
| H0 | Если моста нет, sweep даст **empty** при любом pt — размер не при чём. |

Фактически для сильных слов **H1 отвергнута** в диапазоне 4–240 pt; **H2 частично подтверждена** (сенсорика слабеет, verdict нет); **H0 подтверждена** на пилоте 8 слов.

---

## 3. Метод

| Параметр | Значение |
|----------|----------|
| Store | `agents/von-neumann` |
| Сетка | 32×32, codec `retinal_lrgb` |
| Рендер | `literacy_render.draw_text_centered`, карточка 640×480 |
| Production pt | `build_word_cards._font_size(surface)` |
| Режим **stored** | predict по накопленному lum **без** переимпринта (учебный JPEG) |
| Режим **ephemeral** | перерисовка surface → `imprint_visual_frame` → `predict_lex_for_vis_cue` |
| Запись в store | **нет** |
| Оптимизация | один `resolve_ingest_state` на весь sweep; откат lum между pt |
| Verdict | `probe_lex_verdict`: know / ambiguous / wrong / empty vs `lang.word.*` |

**Исправления в ходе серии:** кириллица на кадре (не slug `mama`); один load store (ранний `--pilot` зависал на перезагрузках).

---

## 4. Прогоны (что вошло в отчёт)

| Run | Команда (суть) | Слова | Диапазон pt | Назначение |
|-----|----------------|-------|-------------|------------|
| **A** | `--pilot` | 8 слов lesson-03 | 20–240 (17 шагов) | сводка по пилоту |
| **B** | `--slugs mama,kot` | мама, кот | 24–240, шаг 8 | контраст know vs ambiguous |
| **C** | кот мелкий | кот | 8–24 | нижняя граница pt |
| **D** | `--frame-ids word-04e9e50c21a5-sans` | предыдущий (10 букв) | 4–240 | длинное слово + know на store |

Сводные таблицы ниже — по **завершённым** прогонам A–D. Файл JSON может быть **перезаписан** узким прогоном (например только D на 4–7 pt); полная копия — восстановить повтором тех же команд из §6 протокола.

---

## 5. Результаты

### 5.1. Пилот 8 слов (run A)

Агрегат **по всем pt 20–240** (на каждом размере картина одна и та же):

| Verdict | Число слов (из 8) | Комментарий |
|---------|-------------------|-------------|
| **know** | 2 | есть устойчивый мост (в т.ч. кот) |
| **ambiguous** | 1 | конкуренция лексем, не «мелкий шрифт» |
| **empty** | 5 | мост не выучен — pt не влияет |

**Вывод по run A:** sweep **не выявляет cliff по pt** на уровне когорты; доминирует **наличие/отсутствие моста**.

### 5.2. Мама и кот (run B, C)

| Слово | Production pt | Stored | Ephemeral 8–240 pt |
|-------|---------------|--------|---------------------|
| **кот** | 200 | **know** | **know** на всех проверенных pt (включая **8 pt**) |
| **мама** | 200 | **ambiguous** (ничья с `grapheme.cyrl.a.lower`) | **ambiguous** на всём диапазоне |

Для **мамы** с ростом pt растёт `top_score`, но лидер не меняется — проблема **дискриминации** буквы «а» внутри слова, не legibility cliff.

### 5.3. Длинное слово «предыдущий» (run D)

| Поле | Значение |
|------|----------|
| `frame_id` | `word-04e9e50c21a5-sans` |
| Букв | 10 |
| Production pt | **120** |
| Stored | **know** |
| Ephemeral **4–240 pt** | **know** на всех шагах (в т.ч. 4, 5, 6, 7, 8 pt) |

**Сенсорика** (ephemeral, ориентир по run D):

| Диапазон pt | `lum_ink_cells` | `lum_bbox` (типично) | Интерпретация |
|-------------|-----------------|----------------------|----------------|
| 8–96 | **0** | 32×32 (весь кадр) | порог «чернил» на 32×2 не срабатывает |
| 104+ | растёт (до **~75** на 240 pt) | сужается | пятно слова становится видимым на решётке |

**Разрыв:** verdict **know** при `lum_ink_cells = 0` → predict идёт по **обученному frame_id**, не по новому отпечатку чернил.

### 5.4. Эвристика порога из JSON

Скрипт считает `threshold_heuristic`: `last_strong_font_pt` / `first_weak_font_pt` при `know_rate ≥ 0.5` по словам в **этом** файле.

На run D (одно слово, все know): `first_weak_font_pt = null` — **нижнего порога не найдено** в заданном диапазоне.

---

## 6. Интерпретация

### 6.1. Два механизма в одном probe

```text
ephemeral imprint (новый размер шрифта)
        │
        ├─► след на 32×2 (lum_ink_cells, bbox)  ──► физика даунсэмпла
        │
        └─► predict_lex_for_vis_cue(frame_id)  ──► голоса E:vis.lum.frame.{id}|…
                    │
                    └─► если мост сильный → know даже при пустом следе
```

Font sweep измеряет **смесь** этих путей. Отделить их:

| Наблюдение | Смысл |
|------------|--------|
| know при `lum_ink_cells = 0` | **память frame_id**, не «прочитал мелкий шрифт» |
| empty на всех pt | нет моста — **сначала ingest**, не fovea |
| ambiguous на всех pt | **конкурирующий grapheme/lex**, не pt |
| рост `lum_ink_cells` с pt без смены verdict | сенсорика богатеет, **дискриминация уже насыщена** |

### 6.2. Связь с ADR-0031 (фовеа)

Оценка «32² хватает для крупной меты» для **нового** чтения по пикселям **не подтверждается** длинными словами на малых pt: след пустой. Оценка «32² хватает для **повторного узнавания учебного frame_id**» для сильных мостов — **подтверждается** до 4–8 pt в этом эксперименте.

Фовеа / 64² нужна, если цель — **перенос на новый размер/шрифт без опоры на старый мост**, а не стабильный recall по id.

### 6.3. Что эксперимент **не** проверяет

- Незнакомое слово / novel `frame_id` (см. `probe_word_recognition_modes`, ADR-0032).
- Семантику «нового слова».
- Другие шрифты (faces), шум на JPEG.
- OCR или побуквенный decode.

---

## 7. Выводы и решения

| # | Вывод | Действие |
|---|--------|----------|
| 1 | Cliff по pt **не найден** для кот / предыдущий при сильном мосте | не ставить «минимальный pt» как gate curriculum |
| 2 | Пилот 5/8 **empty** | приоритет **ingest + probe know**, не font sweep |
| 3 | Мама **ambiguous** | отдельный reinforce / контраст, не legibility |
| 4 | `lum_ink_cells` vs verdict расходятся | в отчётах всегда публиковать **обе** колонки |
| 5 | Ephemeral ≠ «читает с экрана» | в статьях явно писать: **trained bridge transfer** |

---

## 8. Воспроизведение

```powershell
cd Financial/software/open/casa-ontology-payload

# Пилот 8 слов (~20 мин, один writer на store)
python lab/visual-curriculum/probe_font_legibility_sweep.py --pilot

# Пара с контрастом
python lab/visual-curriculum/probe_font_legibility_sweep.py --slugs mama,kot --font-sizes 24,32,40,48,56,64,80,96,112,128,150,180,200,220,240

# Длинное слово
python lab/visual-curriculum/probe_font_legibility_sweep.py --frame-ids word-04e9e50c21a5-sans --font-sizes 4,8,16,24,32,48,64,80,96,104,112,120,128,150,180,200,240
```

Парсинг JSON для сводной таблицы:

```powershell
python -c "import json; from pathlib import Path
r=json.loads(Path('lab/visual-curriculum/generated/teacher-font-legibility-sweep.json').read_text(encoding='utf-8'))
print('words', len(r.get('words',[])))
print('by_font', r.get('by_font_pt'))
print('threshold', r.get('threshold_heuristic'))
print('stored', r.get('stored_baseline'))"
```

---

## 9. Следующие шаги (по данным)

1. **Не** расширять sweep, пока corpus probe не даст приемлемую долю **know** на выбранной когорте.
2. Повтор run B/C/D с сохранением JSON под версионным именем (`teacher-font-legibility-sweep-pilot.json`), чтобы частичные прогоны не затирали сводку.
3. Связать с ADR-0031: пилот **64×64** только для слов с **намеренно слабым** мостом и целью «новый отпечаток», не для кот/предыдущий.
4. Опционально: скрипт `summarize_font_sweep_report.py` → markdown-таблица из JSON (генерация §5 из артефакта).

---

## Приложение: структура JSON

| Поле | Смысл |
|------|--------|
| `words[]` | frame_id, surface, production_font_pt |
| `font_sizes_pt` | сетка эксперимента |
| `by_font_pt[]` | агрегат know_rate по pt |
| `threshold_heuristic` | last_strong / first_weak pt |
| `stored_baseline` | know/total по режиму stored |
| `items[]` | строка на (слово, mode, font_pt): verdict, leaders, lum_* |
