# NCA train core v0 — общая история обучения

## Зачем

В репозитории два семейства «полей памяти», но **одна физика NCA**:

| Источник цели `[K,H,W]` | Скрипт (до унификации) | Размер сетки | K (каналы) |
|-------------------------|------------------------|--------------|------------|
| DMN bundle → grid       | `train_dmn_nca.py`, `train_dmn_nca_windowed.py` | 64×64 | union токенов +8 hidden |
| SSS lattice (L2_word_*) | `train_memory_nca.py`, `train_memory_nca_shards.py` | 32×32 (типично) | слова полки +6 hidden |

Exp J (языковой агент) получил **оконный** цикл раньше: `FieldPlannerV0`, ghost, masked loss, `windows_per_batch` под VRAM. SSS-обучение по 64 полкам оставалось на **полном поле** — дублировались только AMP, damage, rollout из `nca_train_util` / `train_dmn_nca`.

Это не «питонисты vs C#», а два fork одного цикла в скриптах.

## Канон параметров (не менять от прогона к прогону)

`design/nca-train-defaults.json` — решётки, окна, damage, batch cap; загрузка в `tools/nca_train_defaults.py`.

| Профиль | Поле | Окно (tile / stride) | Окна/step |
|---------|------|----------------------|-----------|
| DMN Exp J | 64² | 32 / 16 | auto ≤32 |
| SSS L2 shard | 32² | 16 / 8 | auto ≤32 |

Эпохи в JSON отдельно: `sss_shard_cuda` 80, `dmn_union_full` 1200, `dmn_union_smoke` 600.

## Модуль

`tools/nca_train_core.py`:

- `NcaTrainerConfig` — гиперпараметры, устройство, `channel_extra` (6 для SSS, 8 для DMN).
- `WindowedTrainConfig` — плитка, stride, ghost, batch окон.
- `run_nca_training(..., mode="full"|"windowed")` — единый цикл + best checkpoint.

Низкий уровень уже был общим: `UpdateRule`, `nca_rollout`, `damage_tensor_patches`, `resolve_amp` в `nca_train_util.py`.

## Режимы

### `full`

Весь lattice за шаг (как раньше `train_memory_nca`). На L2 с ~650 каналами это тяжело по VRAM, но просто и достаточно для 32×32.

### `windowed`

Те же оптимизации, что Exp J: планировщик плиток, crop с ghost, loss только внутри tile. Для SSS по умолчанию плитка 16×16, stride 8 на сетке 32×32 — несколько окон за эпоху, меньше активаций на шаг.

## Миграция вызывающих

| Скрипт | Статус |
|--------|--------|
| `train_memory_nca.py` | `--windowed` → core |
| `train_memory_nca_shards.py` | проброс `--windowed` |
| `train_dmn_nca_windowed.py` | пока свой цикл; логику эпохи можно заменить на `run_nca_training` (bundles + mask region остаются в скрипте) |

## Когда что включать

- **Монолит L2_word** (до шардинга) или малый K: `full`.
- **L2_word_XX** (~600–700 W:*), CUDA: `windowed` предпочтительнее.
- **DMN 64×64**, много bundle: уже `train_dmn_nca_windowed.py`; после рефактора — тот же core.

## Сон / inference

Обучение пишет `model.pt` в `{store}/nca/<lattice_id>/`. Sleep и babble не зависят от режима train — только от весов и codec.
