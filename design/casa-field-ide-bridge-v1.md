# CASA field IDE bridge v1 (stage C)

**Command:** `casa_field_query`  
**Flow:** query → match bundle claims → `doc_path` + `section` → Markdown Preview

## Configure

`cascade-ide/.cascade/workspace.toml`:

```toml
[workspace.casa_field]
store_dir = "../casa-ontology-payload/lab/agent-stores/research-agent-lab"
```

Requires agent store populated (`import_knowledge_delta` in lab).

## MCP / agent contract

```json
{"query": "import knowledge delta", "open": true}
```

Returns JSON:

```json
{
  "query": "import knowledge delta",
  "wallMs": 0.42,
  "bundleName": "research-ml.bundle.v1.json",
  "targets": [
    {
      "conceptId": "casa.lab.import_knowledge_delta",
      "docPath": "work/projects/.../ontology-in-field-poc-findings-v1.md",
      "section": "Online learning",
      "sectionLine": 42
    }
  ]
}
```

With `open: true` — opens first target in MFD Markdown Preview scrolled to section line.

## Code

| File | Role |
|------|------|
| `Features/CasaField/Application/CasaFieldQueryResolver.cs` | match query on claims |
| `Features/CasaField/Application/KbSectionLineResolver.cs` | section → line |
| `Features/CasaField/Application/CasaFieldNavigationOpener.cs` | open preview |
| `Services/IdeCommands.Casa.cs` | command id |

Lab side: `tools/sn_cen_infer.py --from-field` (optional; IDE reads bundle directly for nav).
