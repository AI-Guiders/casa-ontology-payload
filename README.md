# casa-ontology-payload

Лаборатория “лёгкой онтологии” поверх Markdown‑KB (agent-notes) и подготовка payload для экспериментов “онтология в поле” (CASA).

**Репозиторий:** https://github.com/AI-Guiders/casa-ontology-payload  
**Open pack (локально):** `Financial/software/open/casa-ontology-payload` (submodule не требуется)

## Идея

- **Ссылки** недостаточны: они адресуют смысл, но не переносят его.
- Поэтому payload состоит из двух частей:
  - **Graph**: узлы (md‑доки) и связи (в v0 просто `references`)
  - **Claims**: извлечённые “атомы смысла” с provenance + `concept_id` (стабильный id)

## Что внутри

- `tools/extract_md_graph.py` — вытянуть graph из Markdown (links → edges).
- `tools/semantic_payload.py` — вытянуть claims и нормализовать `concept_id`.
- `design/layout.v0.json` — региональная композиция одного CA‑поля (DMN/CEN/SN‑аналог) + порты.
- `design/ontology-field-poc-findings-v1.md` — **выводы PoC** (locality, кодеки v0–v3, метрики, рекомендации для v1).
- `tools/codec_grid_v3.py` — placement concepts по provenance (`section` / `doc` / …).
- `examples/` — примеры на проект-карте `ca-substrate-agent` (CASA).

## Быстрый старт

```powershell
python .\tools\extract_md_graph.py .\examples\ca-substrate-agent.README.md --root-id "work/projects/door-to-singularity/ca-substrate-agent/README.md" --out .\examples\ca-substrate-agent.graph.json

python .\tools\semantic_payload.py .\examples\casa-goals-and-roadmap-v1.md --doc-path "work/projects/door-to-singularity/ca-substrate-agent/casa-goals-and-roadmap-v1.md" --out .\examples\casa-goals.payload.json

python .\tools\build_bundle.py --graph .\examples\ca-substrate-agent.graph.json --payload .\examples\casa-goals.payload.json --payload .\examples\research-spec.payload.json --out .\examples\ca-substrate-agent.bundle.v1.json

# “ontology in field” v0: encode → damage → decode (symbolic)
python .\tools\codec_grid_v0.py --bundle .\examples\ca-substrate-agent.bundle.v1.json --out-grid .\examples\grid.json --width 64 --height 64 --copies 7 --damage 0.25 --min-votes 3

# DMN-only region experiment (scaffold; no NCA yet)
python .\tools\train_dmn_stub.py --bundle .\examples\ca-substrate-agent.bundle.v1.json --layout .\design\layout.v0.json --region dmn_ontology --seeds 5 --damage-levels "0.0,0.2,0.4" --out .\examples\dmn_stub_report.json

# DMN-only NCA: recover token grid inside DMN region
python -m pip install -r .\tools\requirements.txt
python .\tools\train_dmn_nca.py --bundle .\examples\ca-substrate-agent.bundle.v1.json --layout .\design\layout.v0.json --region dmn_ontology --damage 0.25 --steps 32 --epochs 400 --out-dir .\examples\nca_out
```

## Канонический пайплайн (v3 + section)

Дефолты: **codec v3**, **concept_mode=section**, patch damage, union train на трёх example bundles.

```powershell
.\scripts\run_canonical.ps1
```

Или по шагам:

```powershell
python .\tools\train_dmn_nca_multibundle.py --bundles .\examples\ca-substrate-agent.bundle.v1.json .\examples\casa-goals.bundle.v1.json .\examples\research-spec.bundle.v1.json --codec v3 --concept-mode section --save-model --out-dir .\examples\nca_out_canonical_v3_section

python .\tools\bench_curve_dmn_nca_union.py --bundle .\examples\ca-substrate-agent.bundle.v1.json --model .\examples\nca_out_canonical_v3_section\model.pt --codec v3 --concept-mode section --out .\examples\nca_v3_section_curve_ca-substrate-agent.bundle.v1_s20.json
```

Дополнительно:

- `tools/build_kb_bundles.py` + `manifests/kb-bundles-ca-substrate-agent.json` — 8 bundle из live KB (`AGENT_NOTES_KB` или `--kb-root`).
- `tools/bench_sweep_decode.py` — sweep threshold / min_votes.
- `tools/demo_goal3_repair.py` — прототип «ошибка → NCA → сравнение» (CASA цель 3).
- `tools/ci_smoke_bench.py` — короткий train+bench для CI.
- `design/embeddings-on-layout-v0.md`, `design/cen-sn-runtime-v0.md` — следующие слои поля.

## Лицензия

MIT (код). Данные KB сюда **не** копируются целиком; `examples/*.md` — маленькие выдержки/сжатые копии для тестов парсинга.

