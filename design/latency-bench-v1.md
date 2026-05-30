# Latency bench v1 (A)

Compare **Qwen (Ollama)** vs **CASA DMN repair** vs **CASA from-field** on the same query.

## Run

```powershell
cd Financial\software\open\casa-ontology-payload
python tools/bench_latency_qwen_casa.py
python tools/bench_latency_qwen_casa.py --skip-qwen   # CASA only
```

Output: `lab/latency_bench_v1/report.json`

## Metrics

| Key | Meaning |
|-----|---------|
| `qwen_ping_warm_ms` | Ollama short prompt (model loaded) |
| `qwen_query_ms` | CASA-like JSON QA prompt |
| `casa_dmn_ms` | `sn_cen_infer` with NCA repair |
| `casa_field_ms` | `sn_cen_infer --from-field` |
| `speedup_field_vs_qwen_query` | ratio |

Requires: agent store populated (`import_knowledge_delta`), Ollama on `:11434` for Qwen rows.
