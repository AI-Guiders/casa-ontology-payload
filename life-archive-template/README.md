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

- `origin` — fetch + push GitHub `AI-Guiders/von-neumann-life-archive` (private → public read при зрелости; см. ADR-0050)
- `backup` + второй push URL на `origin` — Wissance GitLab (зеркало)

Один раз после создания репозитория на GitLab:

```powershell
python tools/sync_life_archive.py setup-backup
```

Или вручную в каталоге life-archive:

```powershell
git remote add backup git@gitlab.wissance.com:wissance/ai/von-neumann-life-archive.git
git remote set-url --push origin https://github.com/AI-Guiders/von-neumann-life-archive.git
git remote set-url --add --push origin git@gitlab.wissance.com:wissance/ai/von-neumann-life-archive.git
git config lfs.https://gitlab.wissance.com/wissance/ai/von-neumann-life-archive.git/info/lfs.locksverify false
```

`snapshot` пушит в `origin` → GitHub и GitLab. Если GitLab LFS падает по TLS, GitHub-часть всё равно уходит; зеркало догоняешь с машины/VPN, где `https://gitlab.wissance.com` открывается.

## Git LFS

`*.pt`, `*.db`, and `field_state*.json` use LFS. Org Free quota: 10 GiB storage + 10 GiB bandwidth/month.

Install once (Windows):

```powershell
winget install GitHub.GitLFS
git lfs install
```

## When to snapshot

After **sleep** or when agent process is **stopped** — avoid half-written checkpoints.
