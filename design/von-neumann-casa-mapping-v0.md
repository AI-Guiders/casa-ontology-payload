# Von Neumann → CASA: перекладка архитектуры

**Status:** design (канон позиции)  
**Date:** 2026-05-28  
**See also:** [`casa-layout-v0.md`](casa-layout-v0.md), [`sss-multi-lattice-z-v0.md`](sss-multi-lattice-z-v0.md), [`second-signal-system-v0.md`](second-signal-system-v0.md), [`layered-ca-pipeline-v0.md`](layered-ca-pipeline-v0.md)

## Идея

Классическая машина фон Neumann — не «устаревший PC», а **контракт**: память + управление + обработка + шина + ввод/вывод.  
CASA **не копирует** x86, но **переносит те же роли** на цилиндр, решётки и CA-динамику.

```text
  Классика                    CASA (наш подход)
  ─────────────────────────────────────────────────────
  Память (единое хранилище)   Цилиндр: стек решёток S[x,y,z_level]
  Шина                        z_bridge + порты P1–P3 + gate.*
  CU (Control Unit)           SN (salience, gate) + FPN (удержание T)
  ALU / исполнение            NCA rollout: repair, compose, digest (z_phase)
  PC / адрес                  active_lattice + active_domain (SN)
  Программа                   z_phase pipeline (encode→repair→digest→gate)
  Данные                      токены на решётках + episodic (опыт в grid)
  I/O                         KB listen (вход), babble/emit (выход), teacher (correct)
```

## Память: не RAM на диске, а цилиндр

| vN | CASA |
|----|------|
| Адресное пространство | `(x, y)` внутри решётки + **`z_level`** (какая решётка) |
| Word | `C:concept_id`, `E:…`, `Z:…` — дискретные токены |
| Единое хранилище программ и данных | **Да, на одном буфере** — топология и активация в одном `field_state`; отличие от PC: **пространственная** структура, не линейный массив |
| Внешняя «память» | git KB, bundles — **I/O**, не адресное пространство CPU |

**ССС** = отдельная **подсистема памяти** внутри цилиндра (вторая сигнальность): стек `L0..L3`, не grep по JSON.

## Шина

| vN | CASA |
|----|------|
| Address/data/control bus | **`z_bridge`** (между решётками), **`digest.*`** (DMN→SN), **`gate.*`** (SN→CEN), **`task.*`** (CEN→DMN) |
| DMA (ввод без CPU) | **Listen**: encode в цилиндр без babble (фоновый T) |
| Interrupt | SN переключает `active_lattice` / режим probe→execute |

Мост L0→L1 — это **шина «compose»**: графемы на нижней решётке **адресуют** слог на верхней (см. [`sss-lattice-stack.v0.json`](sss-lattice-stack.v0.json)).

## Управление (Control Unit)

| vN | CASA |
|----|------|
| Fetch-decode-execute | **Поршень z_phase**: encode → repair → digest → gate ([`layered-ca-pipeline-v0.md`](layered-ca-pipeline-v0.md)) |
| Program counter | **`active_lattice`** + FPN session (цель переживает T) |
| Branch / jump | SN gate: другой z_level, другой домен, probe vs execute |
| Microcode | NCA weights (`model.pt`) — **физика** восстановления, не программа на диске |

CEN — не «ALU», а **исполнитель плана**: babble, запрос к памяти (P3), targets наружу (IDE, тело).

## «Вычисление» (ALU)

У нас **нет** отдельного скалярного ALU. Роль выполняет **локальная CA**:

- **repair** — восстановить повреждённую память;
- **compose (z_bridge)** — поднять паттерн с Lk на Lk+1;
- **digest** — сжать активное в summary для маршрутизации.

Это **spatial computing**: операция = динамика на решётке, не одна инструкция ADD.

## I/O

| vN | CASA |
|----|------|
| Keyboard / tape | Речь среды: KB ingest, dialogue, teacher text |
| Printer / display | **Babble**, `answer_text`, emit (будущее) |
| Block device | agent store на диске — **снимок** цилиндра, не runtime RAM |

**Принцип:** hot path **не читает** `claim.text` как RAM; I/O **впечатывает** в цилиндр (listen), readout **снимает** с решётки (babble).

## Fetch-decode-execute как макро-тик T

```text
T (агент):
  1. I/O?     → listen (encode на z_level)     [ввод]
  2. SN       → fetch digest, set gate         [fetch / branch]
  3. z_phase  → repair + compose bridges       [execute на поле]
  4. CEN      → plan + babble                  [execute / вывод]
  5. correct? → write episodic + repair       [store]
  6. FPN      → удержать цель для T+1         [PC/context]
```

## Чем мы **не** vN-машина

| Классика | CASA |
|----------|------|
| Линейные инструкции | Пространственные правила 3×3 |
| Один PC | Распределённая активность + `active_lattice` |
| Программа в RAM как текст | `z_phase` + обученная NCA |
| Семантика в программе | Семантика **в топологии** решёток и опыте |

## Две сигнальные системы = два «адресных пространства»?

Не обязательно два CPU — **два стека решёток** (или два `subsystem_id`) на одном цилиндре:

- **F\*** — первая сигнальность (math, vis);
- **L\*** — ССС (знаки).

**Hub `E:`** между стеками — как **мост шины** между картой памяти «образ» и картой «слово».

## Несколько цилиндров

PoC — один буфер. Целевое: **`prism_memory`** (LTM, SSS) + **`prism_hippo`** (эпизоды, быстрая запись, **consolidate** → memory). Опционально **`prism_io`** — буфер listen. SN: `active_prism`. Канон: [`multi-cylinder-memory-v0.md`](multi-cylinder-memory-v0.md).

## Lab сегодня

| vN роль | Реализовано | Дальше |
|---------|-------------|--------|
| Память (решётки) | `sss.lattices` L0–L2 | L3, F0 stack |
| Шина | `z_compose` v0 (логика) | NCA `zbr.*` |
| CU | SN/CEN частично | FPN + `active_lattice` в SN |
| ALU | NCA repair (DMN PoC) | train compose bridge |
| I/O | KB → encode; `sss_surface` | listen-only T; correct write |

## Для Cursor

Фон Neumann — **словарь для обсуждения**, не цель «сделать эмулятор PC».  
Говорить: **память = цилиндр/решётки**, **шина = z_bridge + порты**, **CU = SN/FPN**, **исполнение = CA**, **I/O = listen/babble/correct**.
