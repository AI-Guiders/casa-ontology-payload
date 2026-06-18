# Lab snapshots

Frozen **agent stores** для bench и regression. Канонический индекс: [`legacy-agent-stores/INDEX.md`](legacy-agent-stores/INDEX.md).

## Размер

Локально каталог может занимать **~2 GiB** (`ingest-ref-afan`, `lexicon-ru-archaic`, `lexicon-ru-general`, …). Большая часть — `ltm/`, `nca/model.pt`, опциональный `field_state.json`.

## Git policy (целевая)

| Artifact | В git | Примечание |
|----------|-------|------------|
| `MEMORY.md`, `catalog.json`, manifests, bundles | да | метаданные |
| `field_state*.json` | **нет** | rebuild / export LTM |
| `ltm/**/*.ltm` | **нет** | ship via pack export |
| `nca/**/model.pt` | **нет** | re-train или artifact store |

Паттерны в корневом `.gitignore` уже игнорируют `field_state*.json`. Для `ltm/` и `nca/` — не коммитить новые бинарники; исторические — вынести отдельным коммитом (`git rm -r --cached`, без удаления локальных файлов), когда будете готовы чистить history.

## Освободить место (локально, без git)

```powershell
# только field_state (сотни MB каждый) — пересобираются из ltm
Get-ChildItem lab/snapshots -Recurse -Filter 'field_state*.json' | Remove-Item -Force

# полный ingest-ref (read-only corpus mirror) — если не нужен offline
# Remove-Item lab/snapshots/legacy-agent-stores/ingest-ref-afan -Recurse -Force
```

Не удалять `lexicon-*` stores без понимания, какой bench их требует.
