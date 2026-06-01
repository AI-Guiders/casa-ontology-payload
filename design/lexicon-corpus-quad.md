# Lexicon corpus quad v0 (general / tech × EN / RU)

**Date:** 2026-05-30  
**Status:** lab pipeline  
**Parent:** [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`memory-hierarchy.md`](memory-hierarchy.md)

## Цель

Четыре **отдельных agent-store** с полным циклом listen-batch (headwords) + NCA repair. После базовой заливки CASA **только добавляет** новые слова:

- hot path: `predict_t9` / `lexicon_cold_ingest.py` на miss
- sleep: `nca_stale_shards.py --train --device cuda` для новых/shard drift

## Четыре корпуса

| ID | Store | Источник headwords |
|----|-------|-------------------|
| `en-general` | `lexicon-en-general` | export L2 из **`lexicon-en-folk`** (~6700, production EN dictionary) |
| `en-tech` | `lexicon-en-tech` | design/tools/apps/knowledge + seed (`build_tech_headwords`) |
| `ru-general` | `lexicon-ru-general` | **DetCorpus 50k** частотник (CC0), `fetch_ru_frequency_headwords.py` (~50k лемм) |
| `ru-tech` | `lexicon-ru-tech` | KB + design RU/EN scan + seed |

**Важно:** `lexicon-ru-archaic` (Afan sharded) — literary/smoke lineage; **ru-general** = частотник. Позже: `meta.freq.*` + ipm sidecar → sleep ingest объясняет votes/T9.

```bash
python tools/fetch_ru_frequency_headwords.py
```

Сборка всех четырёх списков (Native AOT):

```powershell
dotnet publish apps/Casa.Lexicon.Build/Casa.Lexicon.Build.csproj -c Release -r win-x64
apps/Casa.Lexicon.Build/bin/Release/net10.0/win-x64/publish/casa-lexicon-build.exe quad --root .
```

Проверяет минимумы: EN ≥5k, RU ≥10k. См. `apps/Casa.Lexicon.Build/README.md`.

Старые stores (`lexicon-en-folk`, `lexicon-ru-archaic`) остаются; quad — **ролевое** разбиение для BiT9 и профилей.

## Пайплайн (один раз)

```powershell
cd Financial/software/open/casa-ontology-payload
.\scripts\run_lexicon_corpus_quad.ps1
# или 80 ep: .\scripts\run_lexicon_corpus_quad.ps1 --full-epochs
```

Шаги внутри:

1. Собрать `lab/corpus/*/headwords.v1.txt`
2. `init_lexicon_store.py --corpus-id <id>` → `field_state.json` + `ltm/`
3. `train_memory_nca_shards.py --device cuda` → `{store}/nca/<lattice>/model.pt`
4. `nca_stale_shards.py --sync-registry`
5. `memory_manifest.py --write`

## Инкремент после базы

```bash
# новое слово на sleep / cold path
python tools/lexicon_cold_ingest.py --store-dir lab/agent-stores/lexicon-en-tech --words-file new_words.txt
python tools/nca_stale_shards.py --store-dir lab/agent-stores/lexicon-en-tech --train --device cuda
```

## Поставка

По ADR-0002: ship `ltm/` + `nca/` (+ `nca_train_registry.json`), без `field_state.json` в tar.
