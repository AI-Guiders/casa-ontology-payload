# casa-lexicon-build (Native AOT)

Сборка списков headwords для quad lexicon stores — без Python.

## Сборка

```powershell
cd Financial/software/open/casa-ontology-payload
dotnet publish apps/Casa.Lexicon.Build/Casa.Lexicon.Build.csproj -c Release -r win-x64
```

Бинарник: `apps/Casa.Lexicon.Build/bin/Release/net10.0/win-x64/publish/casa-lexicon-build.exe`

## Команды

| Команда | Назначение |
|---------|------------|
| `quad` | Все 4 корпуса: en-general (sss-en-folk), ru-general (sss-afan), en/ru-tech (scan repo) |
| `export-store` | Один store → headwords file |
| `tech` | Только tech-корпус по locale |

```powershell
.\publish\casa-lexicon-build.exe quad --root .
.\publish\casa-lexicon-build.exe export-store --store-id sss-afan --out lab/corpus/ru-general/headwords.v1.txt
```

Полный пайплайн (headwords + init + NCA): `scripts/run_lexicon_corpus_quad.ps1`

## Источники

- **en-general:** `sss-en-folk` (~6700 слов), не Gutenberg-only
- **ru-general:** `sss-afan` monolith (~42k), **не** junction `sss-ru-lexicon` → sharded smoke
