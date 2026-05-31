# Гиппокамп: стек решёток-специалистов (H0…H3)

**Статус:** design v0 (миграция с монолита `H0_episode`)  
**Дата:** 2026-05-30  
**Родитель:** [`multi-cylinder-memory-v0.md`](multi-cylinder-memory-v0.md)  
**Машиночитаемо:** [`hippo-lattice-stack.v0.json`](hippo-lattice-stack.v0.json)  
**Сосед:** [`sss-lattice-stack.v0.json`](sss-lattice-stack.v0.json) (prism_memory)

## Зачем дробить

Монолит **`H0_episode` + один список `episodes`** — PoC, как когда-то монолитный `L2_word`.

Сейчас в одной куче смешаны:

- исправление поверхности (babble → correct);
- rule / segment episodes (`R:`);
- (roadmap) диалоговые сцены;
- (roadmap) сырой listen до эпизода.

У них **разный sleep-target** в `prism_memory` и разная «химия» записи. Один 32×32 буфер на всё → interference и неясный consolidate.

## Идея

**prism_hippo** — не один organ, а **стек episodic-решёток** (ось `h_level`), по аналогии с L0…L3 в memory:

```text
        h_level (специалисты гиппокампа)
              ↑
    H3 scene  ├──────────────────┐  dialogue → L3_phrase
    H2 rule   ├──── h_bridge ────┤  R: → L3 (+ L2 roadmap)
    H1 surface├──── h_bridge ────┤  T: → L1 / L2_word_XX
    H0 io     ├──────────────────┘  raw listen (roadmap)
              │
    T_sleep: h_bridge_* → prism_memory ; prune ; (опц.) NCA_repair finetune на полках;
             critic-pass → NCA_rule train (regrow validated rule patch; та же math, что repair)
```

**Consolidate scheduler** (`H_replay_queue`) — не решётка, а **очередь replay** на sleep (что прогнать на memory / NCA).

## Решётки

| id | h | Роль | Wake | Sleep → memory |
|----|---|------|------|----------------|
| **H0_io** | 0 | сенсорный буфер utterance | listen сюда, без LTM | promote → H1 или discard |
| **H1_surface** | 1 | babble wrong, teacher word | `append_episode` kind=surface | `_strengthen_concept` → L1 или полка L2 |
| **H2_rule** | 2 | segment / rule hint | `append_rule_episode` | `_strengthen_rule` → L3 (+ L2 позже) |
| **H3_scene** | 3 | turn диалога, cue+контекст | scene listen | bind → L3_phrase |

### Legacy

| Было | Станет |
|------|--------|
| `H0_episode` | **`H1_surface`** (alias до миграции store) |
| все `episodes[]` в одном списке | `episodes` с полем `hippo_lattice_id` или подсписки по shard |

## Мосты `h_bridge_*` (hippo → memory)

Не путать с **z_bridge** (L0→L1 внутри memory) и **KB graph**.

| Мост | От | К | Действие sleep |
|------|----|---|----------------|
| `h_bridge_H1_L1` | H1_surface | L1_syllable | strengthen concept |
| `h_bridge_H1_L2` | H1_surface | L2_word_XX | strengthen + **shard route** по `concept_id` / слову |
| `h_bridge_H2_L3` | H2_rule | L3_phrase | strengthen `R:rule_id` |
| `h_bridge_H3_L3` | H3_scene | L3_phrase | scene / link tokens |
| `h_bridge_H0_io_H1` | H0_io | H1_surface | wake: оформить эпизод |

Код v0: часть уже в `run_sleep` / `_strengthen_rule` — но пишет в общий `H0_episode`. Миграция = **разнести cells** и **маршрут append**.

## SN / CEN

| Поле | Смысл |
|------|--------|
| `active_prism` | `prism_memory` \| `prism_hippo` |
| `active_hippo_lattice` | `H1_surface` … |
| `episode_kind` | surface \| rule \| scene → lattice по таблице в JSON |

CEN при wrong babble не выбирает «куда в LTM», а **куда в hippo**; LTM трогается на **T_sleep**.

## Тики

```text
T_wake:
  listen     → H0_io (roadmap) или сразу memory ingest (массовый корпус)
  babble     → read prism_memory (+ cue из hippo completion — roadmap)
  wrong      → append → H1_surface | H2_rule | H3_scene
  right      → редко прямой tweak memory (исключение)

T_sleep:
  для каждого h_bridge: merge episodes → prism_memory
  H_replay_queue → windowed NCA finetune на memory (roadmap v2)
  prune consolidated; field_version++ на memory
  NCA regrow per lattice (как sss_sleep_all_nca_v0)
```

**KB ingest** (git, bundle) — **I/O с диска**, не замена hippo.  
**Hippo** — **свой опыт** агента (лепет, self-correct, диалог).

## Поставка (etm / tier B)

| Tier | Содержимое |
|------|------------|
| A (prod) | `ltm/` + `nca/` — только **prism_memory** |
| B | + episodic pack **`etm/`** (future): компактные H1…H3 как `.ltm`, очередь episodes в manifest |
| C | episodic не шиппится — только wake experience on device |

`ltm-pack v0` **не включает** hippo (см. [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md)).

## Roadmap (код)

| Версия | Задача |
|--------|--------|
| **v0** | design + JSON; alias `H0_episode` → `H1_surface` в docs |
| **v1** | `append_episode` / `append_rule_episode` → правильная решётка; `episodes[].hippo_lattice_id` |
| **v2** | `run_sleep` по `h_bridge_*`; replay queue + windowed finetune |
| **v3** | `H3_scene` + dialogue ingest; `H0_io` + promote |
| **v4** | `export_etm_pack_v0` / load в runtime без fat JSON |

## Non-goals

- Копировать анатомию DG/CA3/CA1 буквально — только **функциональные** специалисты.
- NCA **на каждый** H* — только если мало каналов и нужен local repair episodic grid; основной NCA остаётся на **memory**.
- Hippo **не** хранит grammar KB и **не** заменяет `ltm/`.

## Связанные документы

| Документ | Роль |
|----------|------|
| [`multi-cylinder-memory-v0.md`](multi-cylinder-memory-v0.md) | prism_hippo vs prism_memory, sleep |
| [`language-acquisition-loop-v0.md`](language-acquisition-loop-v0.md) | listen → babble → correct |
| [`understanding-contract-v0.md`](understanding-contract-v0.md) | Extract → Remember → Use; bench ablation |
| [`l2-lattice-sharding-v0.md`](l2-lattice-sharding-v0.md) | куда consolidate слова |
| [`ltm-pack-v0.md`](ltm-pack-v0.md) | compact LTM shipment |
