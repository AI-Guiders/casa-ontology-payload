# von-neumann life archive

Private transcript of **one agent's living store** — not curriculum, not code.

Synced from `casa-ontology-payload/agents/von-neumann/` via:

```powershell
python tools/sync_life_archive.py snapshot --message "life: after session"
```

## Layout

```text
store/          # mirror of agents/von-neumann at snapshot time
sync_meta.json  # last sync source path + timestamp
```

## Remotes

- `origin` — GitHub `AI-Guiders/von-neumann-life-archive` (private → public read при зрелости; см. ADR-0050)
- add `backup` remote for second host when ready

## Git LFS

`*.pt`, `*.db`, and `field_state*.json` use LFS. Org Free quota: 10 GiB storage + 10 GiB bandwidth/month.

Install once (Windows):

```powershell
winget install GitHub.GitLFS
git lfs install
```

## When to snapshot

After **sleep** or when agent process is **stopped** — avoid half-written checkpoints.
