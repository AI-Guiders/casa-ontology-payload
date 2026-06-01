# CASA-ADR-0018: Vision modality v0 (картинки, не пиксели на L2)

**Статус:** принято (design); код — roadmap v0  
**Дата:** 2026-06-01  
**Область:** `prism_visual`, predict router, ingest, hot→lang bridges  
**Связано:** [`experiment-l-concrete-to-abstract.md`](experiment-l-concrete-to-abstract.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0017-compact-persist.md`](CASA-ADR-0017-compact-persist.md), [`CASA-ADR-0019-control-multi-prism.md`](CASA-ADR-0019-control-multi-prism.md) (отдел зрения в CU), [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md), [`sss-layer-names.md`](sss-layer-names.md) § Vision

---

## Решение (одной фразой)

**Картинки — отдельная модальность и content-призма `prism_visual`**, не расширение `L2_word`. На решётке хранятся **concept_id и якорные токены** (`vis.*`, `V:`), файлы картинок — **вне** поля; hot path **без** CLIP/ViT на каждый tick.

---

## Не путать с текстовым L2

| | Текст (2-я СС) | Vision (1-я СС, Exp L) |
|--|----------------|-------------------------|
| Призма | `prism_memory` / `prism_lang_ru` | **`prism_visual`** |
| Решётки | `L2_word_XX`, `L3_phrase` | **`V1_object`**, `V2_scene` (legacy names) |
| Токен слова | `C:lang.word.хороший`, `W:хороший` | **`C:vis.*`**, `V:vis.animal.cow` |
| Сырьё | строка / cue | **`image_ref`** в bundle + опц. digest при ingest |
| Sharding | 64 шарда по headword | v0: **одна** object-решётка; v1: shard по `vis` namespace при росте vocab |

Remigrate L2 и compact persist **не затрагивают** vision — параллельная работа допустима.

---

## Три слоя «увидеть» (не путать с файлом)

| Слой | Где | Что |
|------|-----|-----|
| **Перцепт** | ingest / `prism_sensor` | растр → codec → embedding / патч-токены |
| **Память образа** | `prism_visual` | `C:vis.*` на `V1_object` |
| **Управление взглядом** | **`prism_control_vis`** ([ADR-0019](CASA-ADR-0019-control-multi-prism.md)) | spotlight, gate, salience по кадру |

Агент «видит образ» = перцепт отпечатан + CU выбрал **куда** читать поле `prism_visual`, не формат `.png`.

---

## Иерархия (ADR-0016)

```text
prism_router
  modality=vis | image  →  prism_visual [, lattice_hint=V1_object]

prism_control_vis (kind=control)     # ADR-0019 — отдел CU
  └── spotlight / gate → mask на prism_visual

prism_visual (kind=content)
  └── V1_object     concept_prefix: vis.     # карточки, объекты
  └── V2_scene      concept_prefix: vis.scene. # сцены (v0 опц.)

prism_hot_context
  └── E: vis.animal.cow → lang.word.корова   # grounding, не дубль cells L2

prism_memory
  └── lang.word.*     уже есть после букваря / lexicon
```

**Мост:** ребра `E:vis.*|same_as|lang.word.*` на visual-решётке + зеркало в hot при listen карточки «картинка + слово».

---

## Формат на решётке (как «хороший», но vis)

Ingest карточки «корова» + `cow.png`:

```text
cells[x,y] += C:vis.animal.cow
              V:vis.animal.cow          # голосование decode (аналог W:)
              E:vis.animal.cow|ground|lang.word.корова
```

- Позиции — тот же **`_place_token` / clustered placement** ([`codec_grid_v1`](../../casa/prisms/shared/codec_grid_v1.py)).
- **`image_ref`** только в claim/bundle и `ltm/meta/vis_refs.json` (audit), не в `.ltm` vocab как bytes.
- **Runtime не открывает файл:** ни SVG, ни PNG на tick не парсятся — агент «видит» только то, что уже отпечатано как `vis.*` / hot / (опц.) `embedding_id`.

---

## Формат файла: не обязан быть SVG

В примерах Exp L часто **`.svg`** (лёгкий букварь в репо). **CASA v0 не «видит» SVG** и не рендерит вектор в hot path — `image_ref` это **opaque path** (как URI внешнего артефакта).

| Формат | В v0 hot path | На ingest (offline) |
|--------|---------------|---------------------|
| **`.png` / `.jpg` / `.webp`** | не декодируется | опц. encoder (CLIP и т.п.) → `embedding_id` + тот же `vis.*` на поле |
| **`.svg`** | не парсится | только как ссылка для UI/человека; для encoder — **растр** (`cow.png`) или pre-render |
| **путь / hash id** | lookup `vis_refs` → `vis.*` | да (символический grounding) |

**Канон v0:** карточка = **`concept_id` + links к `lang.word.*`**; картинка — доказательство для человека и для **offline** ingest. Запрос «что на картинке» в v0 = cue по **id / подписи / уже известному ref**, не CV с нуля.

**v1 (ingest):** `tools/ingest_vis_assets.py` читает **растр**, пишет sidecar `embeddings/<vis_id>.npy` + claim; predict по файлу — **kNN по embedding_id**, всё ещё без ViT на каждый tick (один раз посчитали при заливке).

---

## Bundle / ingest (offline)

```json
{
  "concept_id": "vis.animal.cow",
  "text": "Корова на иллюстрации.",
  "image_ref": "lab/bukvar_vis/animals/cow.png",
  "links": ["lang.word.корова", "lang.word.cow"]
}
```

| Этап | Действие |
|------|----------|
| Bootstrap | `spawn_prism(..., prism_visual)` + `ingest_vis_batch` |
| Encode | claims → `V1_object` cells; edges → `E:` tokens |
| Hot | `add_hot_edge(vis.animal.cow, ground, lang.word.корова)` |
| Compact persist | `prism_id: prism_visual` в `pack.manifest.json` |
| Опц. ingest | raster → encoder → `embedding_id` в claim/sidecar; **не** hot path |

---

## Predict: modality `vis` / `image`

| Cue | Поведение v0 |
|-----|----------------|
| `vis.animal.cow` / id | decode `V1_object` → top `vis.*` |
| текст «корова» | router → `prism_memory`; hot может подтянуть `vis.*` |
| путь `lab/.../cow.png` | lookup `image_ref` index → `vis.*` (таблица, не декод PNG) |
| raw PNG/JPEG bytes в API | **не** в v0 hot path (только pre-ingested `vis.*` / embedding) |

`predict(..., modality="vis")` → `apply_route_for_modality` → `predict_vis` (новый; симметрия `predict_schema`).

---

## Latency (из Exp L)

Hot path остаётся **decode lattice + vote + hot digest**, порядка **15–40 ms** на сотнях vis-claims. Запрещено: ViT/LLM на каждый tick.

---

## Store layout

```text
lab/agent-stores/<id>/
  ltm/visual/V1_object.ltm
  ltm/meta/vis_refs.json          # image_ref → vis.concept_id
  nca/visual/V1_object/model.pt   # опц., sleep repair
```

---

## Roadmap после v0

| Версия | Добавка |
|--------|---------|
| v0 | карточки 50–80 пар, closed-set, bridges к `lang.word.*` |
| v0.1 | `V2_scene`, shard при vocab > cap |
| v1 | transfer@1 на новых картинках (Exp L3) |
| v2 | ingest embedding; retrieve по id, не по пикселям в runtime |

Педагогика: **после** B2 слов ([`experiment-l`](experiment-l-concrete-to-abstract.md)) — L4 букварь картинок.

---

## Код (план)

| Модуль | Роль |
|--------|------|
| `design/prisms/visual/stack.json` | stack SSOT |
| `casa/prisms/visual/ingest_vis.py` | `ingest_vis_batch` |
| `casa/prisms/tick/predictor.py` | `predict_vis`, router branch |
| `prism_spawn` | bootstrap `prism_visual` |
| `export_ltm_pack` | уже multi-prism — включить `prism_visual` |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0018 draft (parallel to L2 remigrate / ADR-0017) |
