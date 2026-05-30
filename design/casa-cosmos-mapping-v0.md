# CASA ↔ NVIDIA Cosmos mapping v0

**Status:** north-star design (analogy, not vendor integration spec)  
**Date:** 2026-05-28  
**Cosmos reference:** [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/) — Predict / Transfer / Reason world foundation models for Physical AI.

## Зачем этот документ

Зафиксировать, что **CASA и Cosmos идут одним архитектурным путём**: несколько **специализированных** моделей/слоёв + **оркестрация**, а не один монолит «всё в одном forward pass».  
Отличие — **субстрат и домен**: Cosmos — видео/физический мир; CASA — **онтология в поле**, KB, агентный маршрут, текст с провенансом.

См. также:

| Аналогия | Файл |
|----------|------|
| fMRI / регионы | [`casa-layout-v0.md`](casa-layout-v0.md), [`modules-fmri-analogy-v0.md`](modules-fmri-analogy-v0.md) |
| **Термины (DMN, SN, CEN, …)** | [`casa-glossary-v0.md`](casa-glossary-v0.md) |
| Поршень (z-фазы) | [`layered-ca-pipeline-v0.md`](layered-ca-pipeline-v0.md) |
| SN / CEN | [`cen-sn-runtime-v0.md`](cen-sn-runtime-v0.md), [`sn-cen-lab-v1.md`](sn-cen-lab-v1.md) |
| Substrate v2 | [`substrate-v2-roadmap.md`](substrate-v2-roadmap.md) |
| RU language lab | [`experiment-j-text-modality-v1.md`](experiment-j-text-modality-v1.md) |

---

## 1. Грубое соответствие семейств

| NVIDIA Cosmos | Роль в Physical AI | CASA (ca-substrate-agent) | Статус CASA |
|---------------|-------------------|---------------------------|-------------|
| **Cosmos Predict** | Предсказание / генерация **следующего состояния мира** (видео) | **DMN** + NCA repair + encode/decode: поле токенов, восстановление после damage, digest | PoC + v2 lab |
| **Cosmos Transfer** | Перенос домена, аугментация (sim → реализм, стиль среды) | **Import / codec tiers**: `import_knowledge_delta`, codec v1→v3, Experiment G/H, union bundles, `kb_field_watcher` | v2 |
| **Cosmos Reason** | VLM: common sense, план, критика, промпты для Predict | **SN** (salience, gate) + **CEN** (task policy, targets, `query_to_dmn`) | v1 lab |
| *(нет прямого аналога в Cosmos)* | — | **Артикуляция** (текст из digest + claims); MoE экспертов речи | **Proposed** (см. §4) |

**Оркестрация Cosmos:** Reason → (критика / план) → Predict / Transfer.  
**Оркестрация CASA:** KB → field → digest → **SN** → **CEN** → (будущее) **articulation**; hot path `--from-field` ~мс.

---

## 2. Один цилиндр vs три чекпоинта

| | Cosmos | CASA |
|---|--------|------|
| Память мира | latent video WFM | дискретное **64×64** поле (**цилиндр**); канон `claims` — **вне** цилиндра, опыт — **в** grid ([`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md)) |
| Параллельность | отдельные модели, pipeline в продукте | **регионы DMN/SN/CEN параллельны на (x,y)** + фазы **z** (поршень) на одном буфере |
| Прозрачность | частично (VLM rationales) | **concept_id**, `doc_path`, `section`, `field_version`, `claims_nav` |
| Типичный GPU | обучение/инференс WFMs | NCA train на 4060+; infer field — CPU/GPU лёгкий |

Поршень ([`layered-ca-pipeline-v0.md`](layered-ca-pipeline-v0.md)):

```text
z=0 encode → z=1 dmn_repair → z=2 digest → z=3 gate
         одно поле (x,y); регионы SN/DMN/CEN сосуществуют на карте
```

---

## 3. Мозг, fMRI, Cosmos — одна ось

| Метафора | Смысл |
|----------|--------|
| **fMRI** (DMN / SN / CEN) | Крупные сети на одном «поле» |
| **Поршень** | Фазы обработки **z** без смены буфера |
| **Cosmos** | Продуктовая декомпозиция WFMs (Predict / Transfer / Reason) |
| **CASA** | Тот же *принцип слоёв*, другой носитель: KB → ontology field → agent |

«Высшие функции» (связная речь) у CASA — **не DMN**, а будущая **кора артикуляции** (§4).

---

## 4. Артикуляция и MoE (proposed)

Текст и «генерация» речи — **высший уровень**, под ними — **не один** блок, а **mixture of specialists** (явный MoE, не только внутри одного transformer).

```text
digest + answer_blocks
        │
        ▼
  CEN policy (answer | open_kb | probe)
        │
        ▼
  Articulation router  ──► expert: ru_grammar | kb_cite | code_nav | dialogue_surface
        │
        ▼
  answer_text (+ provenance)
```

| Эксперт (черновик) | Вход | Выход |
|--------------------|------|--------|
| `compose_ru_grammar` | `claim_kind=rule`, таблицы RU | норма + пример |
| `compose_kb_cite` | top `answer_blocks` | цитата + section |
| `compose_code_nav` | `code_anchors` | кратко + путь |
| `dialogue_surface` | digest + session | связки (обучение / imitation, цель 3) |
| `cosmos_reason` *(опционально, out-of-field)* | видео/физика | не замена поля; соседний WFM |

**Арбитр:** CEN (+ SN gate), как Reason в Cosmos не заменяет Predict, а направляет.

---

## 5. Когда что использовать (политика v0)

| Ситуация | Путь |
|----------|------|
| Запрос попадает в KB / field (высокий match) | CASA hot path: decode → SN → CEN → compose/MoE |
| Нужен канон, русская грамматика, CASA docs | `language-agent-lab-v0`, Experiment J |
| Физика, видео, робот, длинный visual context | **Cosmos** Predict / Reason (отдельный контур) |
| Out-of-KB «любая тема» | опционально локальный LM / Cosmos Reason — **не** память агента |

Память агента остаётся в **поле + git + agent-notes**; внешние WFMs — **поверхность**, не источник правды.

---

## 6. Железо и «без дата-центра»

| | Cosmos (типично) | CASA (сейчас) |
|---|------------------|---------------|
| Train | кластер / DGX | локальная GPU (4060), union NCA |
| Infer WFMs | GPU, NIM | field decode + SN/CEN — **мс** |
| Масштаб «как Cosmos дома» | DGX Spark и т.п. | тот же железный класс: train поля + опционально Reason/articulation local |

---

## 7. Roadmap (согласование с Cosmos-путём)

| Этап | CASA | Cosmos-параллель |
|------|------|------------------|
| Done | DMN PoC, G/H, union, watcher, IDE bridge | Predict/Transfer/Reason как **внешний** референс |
| Done | SN/CEN v2, `answer_blocks`, RU bundles (Exp J) | Reason ≈ CEN; retrieval ≈ часть Reason |
| Next | `answer_compose` + articulation MoE v0 | специализированные «мини-модели» выхода |
| Next | `T:` tokens on field (Exp J phase 2) | Predict-like **state** на поле, не видео |
| Later | imitation + repair на артикуляции (цель 3) | post-train WFMs, но на **своём** субстрате |
| Optional | Cosmos Reason для video/physical tool | federated agent card, не merge в DMN |

---

## 8. Non-goals (v0)

- Не дублировать Cosmos Predict для текста/KB.
- Не смешивать VLM weights с `field_state.json`.
- Не называть один LLM hook «памятью» — память = DMN + KB + import.

---

## 9. Ссылки

- NVIDIA Cosmos: https://www.nvidia.com/en-us/ai/cosmos/
- Docs: https://docs.nvidia.com/cosmos/latest/introduction.html
- KB canon (mirror): `agent-notes` → `work/projects/door-to-singularity/ca-substrate-agent/casa-goals-and-roadmap-v1.md`
- Repo: https://github.com/AI-Guiders/casa-ontology-payload
