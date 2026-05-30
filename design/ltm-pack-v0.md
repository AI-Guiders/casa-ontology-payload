# LTM pack v0 — компактная поставка памяти

**Статус:** lab v0 (`ltm_pack_v0.py`, `export_ltm_pack_v0.py`, `import_ltm_pack_v0.py`)  
**Дата:** 2026-05-30  
**ADR (решение):** [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md)  
**См. также:** [`memory-hierarchy-v0.md`](memory-hierarchy-v0.md), [`l2-lattice-sharding-v0.md`](l2-lattice-sharding-v0.md)

## Проблема

`field_state.json` (~400 MiB) дублирует строки токенов в каждой `cells[]`.  
NCA `model.pt` (~2 MiB/полка) чинит **известную раскладку**, а не заменяет лексикон.

В продакшен-поставке не тащим prettified JSON — см. ADR-0002.

## Раскладка в agent store

```text
{store}/
├── ltm/                          # компактная память (v0)
│   ├── pack.manifest.json        # маршрут, l2_sharding, реестр nca
│   ├── l0/L0_grapheme.ltm
│   ├── l1/L1_syllable.ltm
│   └── l2/L2_word_07.ltm         # опционально .ltm.zst
├── nca/L2_word_07/model.pt
└── field_state.json              # только лаб / merge
```

## Бинарник `.ltm` (одна решётка)

| Секция | Содержимое |
|--------|------------|
| header | magic `LTM0`, version, width, height, vocab_count, placement_count |
| vocab | строки токенов (UTF-8), один раз |
| placements | `(token_idx u16, x u8, y u8)` на вхождение (копии сохраняются) |

Метаданные решётки (`z_level`, `concept_prefix`, …) — в `pack.manifest.json`.

## Уровни поставки

| Уровень | Состав | Назначение |
|---------|--------|------------|
| **A** | `ltm/` + `nca/` | runtime (pack → поле в RAM) |
| **B** | + `field_state.json` | разработка, diff, legacy |
| **C** | headwords + рецепт rebuild (будущее) | минимальный дистрибутив |

## Команды

```bash
python tools/export_ltm_pack_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0
python tools/import_ltm_pack_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0
python tools/export_ltm_pack_v0.py --store-dir … --compress   # .ltm.zst if zstandard installed
```

## Round-trip

Export → import воспроизводит те же `cells` на каждой решётке.  
`field_version` и episodic-цилиндры import-v0 **не** трогает (только memory-lattices).
