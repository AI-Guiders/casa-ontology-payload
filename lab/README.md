# CASA lab

Локальная песочница: корpora, frozen agent stores, эксперименты и отчёты. **Prod runtime** — `agents/`, не `lab/`.

## Карта каталогов

| Путь | Назначение | Git |
|------|------------|-----|
| [`text/`](text/) | Текстовые корpora (Afan, headwords, кэш fb2) | tracked |
| [`corpus/`](corpus/) | Производные lexicon/frequency (manifests tracked) | частично |
| [`kb/`](kb/) | KB bundles и payloads для import/bench | tracked |
| [`bundles/`](bundles/) | Reference bundles для union3 / NCA bench (ca-substrate, casa-goals, research-spec) | tracked |
| [`snapshots/`](snapshots/) | Frozen lab agent stores (`legacy-agent-stores/`) | tracked (см. ниже) |
| [`agent-stores/`](agent-stores/) | Активные role-based stores (math, language, control…) | см. INDEX в snapshots |
| [`reports/`](reports/) | JSON-отчёты bench/demo | tracked |
| [`exp_*/`](.) | Одноразовые эксперименты + локальный output | **ignored** |
| [`exp_listen/`](exp_listen/) | Multimodal listen / womb ingest (видео, srt, frames) | **ignored** |
| [`nca_out*/`](.) | Scratch после NCA train/bench | **ignored** |
| [`out/`](out/), [`layered_out/`](layered_out/) | Прочий generated output | **ignored** |
| [`visual-curriculum/`](visual-curriculum/) | Visual moment curriculum | mixed |
| [`scripts/`](scripts/) | Lab-only утилиты | tracked |

## Правила гигиены

1. **Не сыпать в корень `lab/`** — bundles → `bundles/` или `kb/`, bench JSON → `reports/`, scratch → `_scratch/` (ignored).
2. **`_tmp*` / `_bench*`** — одноразовый мусор, в `.gitignore`; удалять после прогона.
3. **`nca_out*`** — пересоздаваемый train output; можно `Remove-Item lab/nca_out* -Recurse -Force` когда место нужно.
4. **Afan / archaic** — только NCA smoke; для listen/womb — modern corpus (`design/ru-lexicon-modern-archaic.md`).

## Snapshots (~1.9 GiB локально)

[`snapshots/legacy-agent-stores/`](snapshots/legacy-agent-stores/INDEX.md) — lexicon, ingest-ref, control stack. Тяжёлые артеfact'ы:

- `field_state*.json` — уже в `.gitignore` (rebuild from LTM)
- `ltm/`, `nca/` — **не должны** жить в git long-term; см. [`snapshots/README.md`](snapshots/README.md)

Пересборка LTM pack:

```bash
python tools/export_ltm_pack.py --store-dir lab/snapshots/legacy-agent-stores/lexicon-ru-archaic
```

## Multimodal womb (listen)

[`exp_listen/masha-womb-v0/`](exp_listen/masha-womb-v0/) — «Маша и каша», clip + srt + frames. Контракт ingest: [`design/CASA-scratch-multimodal-moment-binding-v1.md`](../design/CASA-scratch-multimodal-moment-binding-v1.md).

## Быстрая уборка (локально)

```powershell
# scratch (ignored)
Remove-Item lab/_tmp*, lab/_bench* -Force -ErrorAction SilentlyContinue
Remove-Item lab/**/*.log -Force -ErrorAction SilentlyContinue

# NCA train dirs (ignored, ~десятки MB)
Get-ChildItem lab -Directory -Filter 'nca_out*' | Remove-Item -Recurse -Force

# пустые smoke dirs
Get-ChildItem lab -Directory | Where-Object { -not (Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue) } | Remove-Item -Force
```
