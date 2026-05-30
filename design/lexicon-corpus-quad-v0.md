# Lexicon corpus quad v0 (general / tech × EN / RU)

**Date:** 2026-05-30  
**Status:** lab pipeline  
**Parent:** [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`memory-hierarchy-v0.md`](memory-hierarchy-v0.md)

## Цель

Четыре **отдельных agent-store** с полным циклом listen-batch (headwords) + NCA repair. После базовой заливки CASA **только добавляет** новые слова:

- hot path: `predict_t9` / `lexicon_cold_ingest_v0.py` на miss
- sleep: `nca_stale_shards_v0.py --train --device cuda` для новых/shard drift

## Четыре корпуса

| ID | Store | Источник headwords |
|----|-------|-------------------|
| `en-general` | `sss-en-general-v0` | export L2 из **`sss-en-folk-v0`** (~6700, production EN dictionary) |
| `en-tech` | `sss-en-tech-v0` | design/tools/apps/knowledge + seed (`build_tech_headwords_v0`) |
| `ru-general` | `sss-ru-general-v0` | **DetCorpus 50k** частотник (CC0), `fetch_ru_frequency_headwords_v0.py` (~50k лемм) |
| `ru-tech` | `sss-ru-tech-v0` | KB + design RU/EN scan + seed |

**Важно:** `sss-ru-lexicon-v0` (Afan sharded) — literary/smoke lineage; **ru-general** = частотник. Позже: `meta.freq.*` + ipm sidecar → sleep ingest объясняет votes/T9.

```bash
python tools/fetch_ru_frequency_headwords_v0.py
```

Сборка всех четырёх списков (Native AOT):

```powershell
dotnet publish apps/Casa.Lexicon.Build/Casa.Lexicon.Build.csproj -c Release -r win-x64
apps/Casa.Lexicon.Build/bin/Release/net10.0/win-x64/publish/casa-lexicon-build.exe quad --root .
```

Проверяет минимумы: EN ≥5k, RU ≥10k. См. `apps/Casa.Lexicon.Build/README.md`.

Старые stores (`sss-en-folk-v0`, `sss-ru-lexicon-v0`) остаются; quad — **ролевое** разбиение для BiT9 и профилей.

## Пайплайн (один раз)

```powershell
cd Financial/software/open/casa-ontology-payload
.\scripts\run_lexicon_corpus_quad_v0.ps1
# или 80 ep: .\scripts\run_lexicon_corpus_quad_v0.ps1 --full-epochs
```

Шаги внутри:

1. Собрать `lab/corpus/*/headwords.v1.txt`
2. `init_lexicon_store_v0.py --corpus-id <id>` → `field_state.json` + `ltm/`
3. `train_sss_nca_shards_v0.py --device cuda` → `{store}/nca/<lattice>/model.pt`
4. `nca_stale_shards_v0.py --sync-registry`
5. `sss_memory_manifest_v0.py --write`

## Инкремент после базы

```bash
# новое слово на sleep / cold path
python tools/lexicon_cold_ingest_v0.py --store-dir lab/agent-stores/sss-en-tech-v0 --words-file new_words.txt
python tools/nca_stale_shards_v0.py --store-dir lab/agent-stores/sss-en-tech-v0 --train --device cuda
```

## Поставка

По ADR-0002: ship `ltm/` + `nca/` (+ `nca_train_registry.v0.json`), без `field_state.json` в tar.
