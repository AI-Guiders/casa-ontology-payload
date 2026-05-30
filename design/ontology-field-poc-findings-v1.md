# Ontology in field — выводы PoC (v1)

**Дата:** 2026-05-28  
**Статус:** зафиксировано по результатам лаборатории `casa-ontology-payload`  
**Канон (KB):** `work/projects/door-to-singularity/ca-substrate-agent/ontology-in-field-poc-findings-v1.md`

## 1) Зачем этот документ

Зафиксировать **воспроизводимые** выводы экспериментов «онтология в поле» (encode → damage → NCA → decode → F1), чтобы при проектировании CASA v1 не потерять главный инженерный принцип: **кодек = геометрия смысла**, а не сериализация JSON.

## 2) Постановка

- **Вход:** bundle = graph (md-узлы + edges) + claims (`concept_id`, text, `doc_path`, `section`).
- **Поле:** дискретные токены в DMN-регионе (см. `layout.v0.json`).
- **Повреждение:** patch-дыры внутри DMN (прямоугольные патчи; severity ∝ число патчей).
- **Восстановление:** локальное правило NCA (48 шагов), затем `decode_grid` (голосование ≥ `min_votes`).
- **Метрики:** Precision / Recall / F1 отдельно по `concept_id` и по `edges`.

## Репозиторий (карточка)

| | |
|--|--|
| **GitHub** | https://github.com/AI-Guiders/casa-ontology-payload |
| **Open pack** | `Financial/software/open/casa-ontology-payload` |
| **nca-lab bridge** | `Financial/software/open/nca-lab/ontology-field/README.md` |
| **Submodule** | не используется — клон/соседняя папка достаточно |

## 3) Главный принцип (locality contract)

> Для каждого типа сущности **X**: *какой локальный контекст достаточен, чтобы восстановить X после damage?*  
> Разместить X на поле так, чтобы контекст попадал в радиус влияния sub-CA.

| Тип | Локальный контекст | Кодек |
|-----|-------------------|--------|
| **Edge** | узлы `N:src`, `N:dst` | `codec_grid_v2` — кластер у midpoint |
| **Concept** | `(doc_path, section)` | `codec_grid_v3`, mode **`section`** |
| **Node** | якорь документа | v2/v3 |

**Аналогия:** Zettelkasten на CA-поле (атомы + хабы + локальные связи). Источник — KB Markdown.

## 4) Эволюция кодеков

| Версия | Идея | Итог |
|--------|------|------|
| v0 | LCG по всему полю | NCA ≈ baseline |
| v1 | кластеры без семантики | мало переносимости |
| v2 | edges у midpoint узлов | **+Δ edges F1** |
| v3 | concepts у section hub | **+Δ concepts F1** (`section`) |

## 5) Цифры (ориентиры, 20 seeds)

**Edges** (v2, patch, multi-bundle): при damage≈0.4 edges F1 **0.413→0.436**; при 0.6 **0.291→0.352**.  
Артефакты: `lab/nca_union3_codec2_patches_w8_curve2_*_s20.json`

**Concepts** (v3, damage=0.4): средний Δ по 3 bundle — `independent` ~0.003, `doc` ~0.005, **`section` ~0.075**, `doc_section` ~0.20 (нестабильно на малых bundle).  
Артефакт: `lab/concept_locality_bench.json`

## 6) Рекомендации для CASA v1

1. DMN-кодек: **v3 + `section`** + edges как v2.  
2. Damage: **patches**; severity от доли площади DMN.  
3. Embeddings (HCI-стиль) — **поверх** layout, не вместо.  
4. Регионы DMN/CEN/SN — без изменений контракта (`casa-layout-v0.md`).

## 7) Шпаргалка команд

```powershell
python .\tools\codec_grid_v3.py --bundle .\lab\ca-substrate-agent.bundle.v1.json --concept-mode section --out-grid .\lab\grid.v3.json
python .\tools\train_dmn_nca_multibundle.py --codec v3 --concept-mode section --damage-mode patches --damage-patches 8 --bundles .\lab\ca-substrate-agent.bundle.v1.json .\lab\casa-goals.bundle.v1.json .\lab\research-spec.bundle.v1.json --save-model --out-dir .\lab\nca_out_v3_section
python .\tools\bench_concept_locality.py --damage 0.4 --out .\lab\concept_locality_bench.json
```
