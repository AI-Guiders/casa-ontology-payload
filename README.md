# casa-ontology-payload

Лаборатория “лёгкой онтологии” поверх Markdown‑KB (agent-notes) и подготовка payload для экспериментов “онтология в поле” (CASA).

## Идея

- **Ссылки** недостаточны: они адресуют смысл, но не переносят его.
- Поэтому payload состоит из двух частей:
  - **Graph**: узлы (md‑доки) и связи (в v0 просто `references`)
  - **Claims**: извлечённые “атомы смысла” с provenance + `concept_id` (стабильный id)

## Что внутри

- `tools/extract_md_graph.py` — вытянуть graph из Markdown (links → edges).
- `tools/semantic_payload.py` — вытянуть claims и нормализовать `concept_id`.
- `design/layout.v0.json` — региональная композиция одного CA‑поля (DMN/CEN/SN‑аналог) + порты.
- `examples/` — примеры на проект-карте `ca-substrate-agent` (CASA).

## Быстрый старт

```powershell
python .\tools\extract_md_graph.py .\examples\ca-substrate-agent.README.md --root-id "work/projects/door-to-singularity/ca-substrate-agent/README.md" --out .\examples\ca-substrate-agent.graph.json

python .\tools\semantic_payload.py .\examples\casa-goals-and-roadmap-v1.md --doc-path "work/projects/door-to-singularity/ca-substrate-agent/casa-goals-and-roadmap-v1.md" --out .\examples\casa-goals.payload.json

python .\tools\build_bundle.py --graph .\examples\ca-substrate-agent.graph.json --payload .\examples\casa-goals.payload.json --payload .\examples\research-spec.payload.json --out .\examples\ca-substrate-agent.bundle.v1.json

# “ontology in field” v0: encode → damage → decode (symbolic)
python .\tools\codec_grid_v0.py --bundle .\examples\ca-substrate-agent.bundle.v1.json --out-grid .\examples\grid.json --width 64 --height 64 --copies 7 --damage 0.25 --min-votes 3
```

## Лицензия

MIT (код). Данные KB сюда **не** копируются целиком; `examples/*.md` — маленькие выдержки/сжатые копии для тестов парсинга.

