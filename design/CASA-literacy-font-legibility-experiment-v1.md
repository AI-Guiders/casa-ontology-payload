# Эксперимент: порог шрифта на сетке 32×32 (v1)

**Статус:** lab-диагностика  
**Аналитический отчёт (прогоны 2026-06):** [CASA-literacy-font-legibility-report-v1.md](CASA-literacy-font-legibility-report-v1.md)  
**Связано:** [CASA-ADR-0031-foveated-saccadic-visual-sampling.md](CASA-ADR-0031-foveated-saccadic-visual-sampling.md) (оценка «32² достаточно для крупной меты»), `lessons/literacy-cards/tools/literacy_render.py`, `build_word_cards._font_size`

---

## Вопрос

При **текущем** codec `retinal_lrgb` и **32×32** lum — при каком размере шрифта (PIL pt на карточке 640×480) агент **перестаёт** узнавать **уже выученное** слово (`lang.word.*`) на held-out рендере?

Это **данные**, не таблица из ADR.

---

## Протокол

| Шаг | Действие |
|-----|----------|
| 1 | Слова уже в store (ingest corpus/pilot). |
| 2 | **Не** пишем в store. |
| 3 | Для каждой пары `(слово, font_pt)`: загрузить state → нарисовать текст → **ephemeral** `imprint_visual_frame` → `predict_lex_for_vis_cue` → verdict vs `concept_id`. |
| 4 | Параллельно: **метрики следа** на 32×2 (`lum_ink_cells`, `lum_bbox_w/h`) — физика даунсэмпла. |
| 5 | Сводка `know_rate` по `font_pt`; эвристика `last_strong_font_pt` / `first_weak_font_pt` (порог know_rate ≥ 0.5). |

**Режим `stored`:** predict без переимпринта — «что помнит с прошлых уроков на production JPEG».  
**Режим `ephemeral`:** честный тест **нового** размера при старых мостах.

---

## Что уже есть в репо (не дублировать)

| Утилита | Роль |
|---------|------|
| `lessons/literacy-cards/tools/literacy_render.py` | карточка 640×480, `draw_text_centered`, `font()` |
| `build_word_cards._font_size` | production pt по длине слова |
| `lab/visual-curriculum/probe_infra.py` | store lock, отчёт в `generated/` |
| `probe_lex_verdict.py` | know / ambiguous / wrong / empty |
| `predict_lex_for_vis_cue` + `imprint_visual_frame` | read path 32×32 |

`probe_font_legibility_sweep.py` — только **sweep** (много pt × ephemeral imprint); рендер идёт через `literacy_render`.

## Запуск

```powershell
cd Financial/software/open/casa-ontology-payload
python lab/visual-curriculum/probe_font_legibility_sweep.py --pilot
# уже обученные слова корпуса (по slug):
python lab/visual-curriculum/probe_font_legibility_sweep.py --slugs mama,kot,дом --font-sizes 32,48,64,80,96,120,150,180,220
```

| Артефакт | Назначение |
|----------|------------|
| `lab/visual-curriculum/generated/teacher-font-legibility-sweep.json` | сырые строки probe (machine-readable) |
| [CASA-literacy-font-legibility-report-v1.md](CASA-literacy-font-legibility-report-v1.md) | **аналитический отчёт**: выводы, таблицы, интерпретация |

При частичном перезапуске JSON не затирать сводку — писать в `--out …-pilot.json` или копировать перед новым sweep (см. отчёт §8).

---

## Интерпретация (кратко; полный разбор — в отчёте)

| Наблюдение | Смысл |
|------------|--------|
| `know_rate` падает при малых `font_pt`, `lum_ink_cells` тоже | лимит **сенсорики** 32×2 |
| `stored` know, `ephemeral` empty при production pt | мосты не совпадают с текущим imprint (переучить / другой frame) |
| `know` только на production pt | узнаёт **обученный** размер, не перенос |
| cliff при ~N pt | кандидат для fovea ADR-0031 или 64² пилота |

---

## Три смысла «знать слово» (не смешивать)

| Твой вопрос | Режим probe | Что измеряем |
|-------------|-------------|--------------|
| **1. Узнаю и отличаю от других** (не полная семантика) | `L1_trained_bridge` | мост `vis.lum.frame.*` → `lang.word.*`; hint = teacher; verdict know/ambiguous |
| **2. Новое слово = гипотезы, контекст, части** | *не этот probe* | отдельный трек meta/grammar, J0 — не font sweep |
| **3. Не видел целое слово; слоги/буквы** | `L3_never_ingested` + `grapheme_syllable_top` | novel `frame_id`, нет урока на id; смотрим grapheme/syllable в top-k (диагностика; bind к `lang.word.*` — [CASA-ADR-0032](CASA-ADR-0032-analytic-syllable-reading.md) R1/R2) |

Дополнительно: **`L2_imprint_cells`** — тот же текст, но **другой frame_id** и predict **без рёбер** lexicon (только lum). Ближе к «читаемость 32×2», дальше от «помню урок».

Скрипт: `probe_word_recognition_modes.py` — отчёт `teacher-word-recognition-modes.json`.

```powershell
python lab/visual-curriculum/probe_word_recognition_modes.py `
  --frame-ids word-04e9e50c21a5-sans,word-79ace4ce330a-sans `
  --font-sizes 8,48,120,200
```

Пара **предыдущий** (учили, know) vs **неученое длинное** (empty на L1 stored).

---

## Ограничения v1

- Один шрифт (Segoe/Arial из `literacy_render`).
- Не меняет `DEFAULT_GRID_SIZE`.
- Не учит новые размеры — только диагностика transfer.
- Длинные слова и короткие в одном sweep — разный production pt (`_font_size`).

---

## Следующие шаги (по данным)

1. Повтор на 3–5 длинах слова (2, 4, 8 букв).
2. Сравнить `lum_bbox_w` с cliff know_rate — калибровка порога **ячеек**.
3. Отдельный ingest-stage «мелкий шрифт» только если нужен **учёт**, не только probe.
