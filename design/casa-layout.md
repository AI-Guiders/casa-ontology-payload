# CASA layout v0 (region-based, fMRI-inspired)

Цель: зафиксировать **региональную** композицию одного большого CA‑поля (как “сети” в fMRI), чтобы:

- было что **кодировать** (payload),
- было что **повреждать** (damage),
- было что **восстанавливать** (recovery),
- и было понятно, **куда** вводить “переключатель/арбитр” (salience/router).

Это дизайн‑контракт для прототипа; не утверждение о биологии.

## 1) Принцип: один CA, несколько регионов

Мы считаем, что есть одно поле \(H\times W\) с \(C\) каналами на клетку.

**Несколько «решёток» внутри DMN** (слои букваря B0→B3, домены `lang` / `math` / `vis` по sub-rect или по **y**/ **x**) — **разрешены контрактом**: один цилиндр, SN маршрутизирует **какой** sub-rect и слой активен (gate + digest mask). См. [`bukvar-text-modality.md`](bukvar-text-modality.md) § «Несколько решёток». v0 lab пока кладёт union в один `dmn_ontology`; v1 — `layout.v1` с bands/domains.

Регион (sub‑CA) задаётся:

- прямоугольником координат,
- списком “роль/контракт”,
- списком портов (узкие мосты между регионами),
- допустимыми каналами для чтения/записи.

## 2) Тройка сетей (аналог DMN/CEN/SN)

Упрощённый mapping, не буквальная нейро‑анатомия:

- **DMN‑аналог = Ontology/Memory**: держит смысловой payload (bundle), переживает damage, отдаёт digest.
- **CEN‑аналог = Planner/Executor**: решает текущую задачу, читает digest, пишет запрос/действие.
- **SN‑аналог = Router/Salience**: переключает каналы/порты (gating), решает “что важно сейчас”.

## 3) Layout v0 (64×64)

```text
0,0                              63,0
+----------------------------------+
|          Ontology / DMN          |  x:0..31, y:0..63
|                                  |
|                                  |
|                                  |
|                                  |
+--------------------+-------------+
| Router / SN        | Planner/CEN |
| x:32..63,y:0..31   | x:32..63,y:32..63
|                    |             |
+--------------------+-------------+
```

Порты (мосты):

- **P1 (DMN→SN)**: узкий канал передачи “digest” (идентификаторы concept_id + сигнал уверенности).
- **P2 (SN→CEN)**: канал gate/режима (что читать/писать) + “attention mask”.
- **P3 (CEN→DMN)** *(опционально)*: запрос на память (“дай концепты по теме”).

## 4) Каналы (минимальный набор)

В v0 достаточно **символьных** (дискретных) каналов поверх `codec_grid`:

- `tok_*`: кодирование токенов (concept/edge) в регионе DMN.
- `digest_*`: узкий summary, который SN читает и маршрутизирует.
- `gate_*`: гейтинг каналов/портов (SN пишет, остальные читают).
- `task_*`: текущая задача/контекст, который CEN пишет/читает.

Реальные численные каналы NCA (continuous) появятся позже; сейчас фиксируем **контракт**.

## 5) Артефакты

- `design/layout.json` — машинно‑читаемое описание регионов/портов/каналов.
- `design/ontology-field-poc-findings-v1.md` — выводы PoC «онтология в поле» (locality, кодеки, F1).
- `design/embeddings-on-layout.md` — stub: embeddings поверх layout (не вместо provenance).
- `design/cen-sn-runtime.md` — контракт SN/CEN после DMN PoC.
- `design/casa-cosmos-mapping.md` — north star: CASA ↔ NVIDIA Cosmos (Predict / Transfer / Reason).
- `design/casa-glossary.md` — глоссарий: DMN, SN, CEN, FPN, порты, bundle, hot path.
- `design/fpn-control-region.md` — **proposed** v1: четвёртый регион FPN (layout B).
- Канон KB: `work/projects/door-to-singularity/ca-substrate-agent/ontology-in-field-poc-findings-v1.md`.
- Репо: https://github.com/AI-Guiders/casa-ontology-payload · локально `Financial/software/open/casa-ontology-payload`.

