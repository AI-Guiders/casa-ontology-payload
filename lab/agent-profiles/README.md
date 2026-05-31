# Agent profiles v0

Рецепты продуктов поверх **одного CASA core** + **agent store** (`ltm/` + `nca/`).

Канон: [`design/CASA-ADR-0007-agent-profile-store-packs.md`](../../design/CASA-ADR-0007-agent-profile-store-packs.md)

| Profile | Продукт | Статус |
|---------|---------|--------|
| [`bilingual-t9-console.json`](bilingual-t9-console.json) | RU+EN T9, C# console | **lab green** |
| [`dev-ide-complete.json`](dev-ide-complete.json) | IDE autocomplete via MCP | roadmap |

Перед поставкой store — **export ltm** (канон):

```bash
python tools/export_ltm_pack.py --store-dir lab/agent-stores/sss-ru-lexicon
python tools/export_ltm_pack.py --store-dir lab/agent-stores/sss-en-folk
```

Boot по profile (сейчас вручную):

```bash
python tools/boot_linked_stores.py \
  --ru-store lab/agent-stores/sss-ru-lexicon \
  --en-store lab/agent-stores/sss-en-folk
python tools/run_t9_demo_cycle.py
```

Planned: `run_agent_profile.py --profile lab/agent-profiles/bilingual-t9-console.json`
