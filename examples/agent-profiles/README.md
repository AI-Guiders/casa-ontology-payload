# Agent profiles v0

Рецепты продуктов поверх **одного CASA core** + **agent store** (`ltm/` + `nca/`).

Канон: [`design/CASA-ADR-0007-agent-profile-store-packs.md`](../../design/CASA-ADR-0007-agent-profile-store-packs.md)

| Profile | Продукт | Статус |
|---------|---------|--------|
| [`bilingual-t9-console.v0.json`](bilingual-t9-console.v0.json) | RU+EN T9, C# console | **lab green** |
| [`dev-ide-complete.v0.json`](dev-ide-complete.v0.json) | IDE autocomplete via MCP | roadmap |

Перед поставкой store — **export ltm** (канон):

```bash
python tools/export_ltm_pack_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0
python tools/export_ltm_pack_v0.py --store-dir examples/agent-stores/sss-en-folk-v0
```

Boot по profile (сейчас вручную):

```bash
python tools/boot_linked_stores_v0.py \
  --ru-store examples/agent-stores/sss-ru-lexicon-v0 \
  --en-store examples/agent-stores/sss-en-folk-v0
python tools/run_t9_demo_cycle_v0.py
```

Planned: `run_agent_profile_v0.py --profile examples/agent-profiles/bilingual-t9-console.v0.json`
