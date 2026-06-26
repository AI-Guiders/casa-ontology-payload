# Scratch: branch digest — (h+a)(h+a) coordination

**Status:** scratch — session ritual, not calendar  
**Date:** 2026-06-16  
**Parent:** team process; complements [`CASA-scratch-track-integration-v1.md`](CASA-scratch-track-integration-v1.md), [`CASA-scratch-listen-wire-gap-v1.md`](CASA-scratch-listen-wire-gap-v1.md), ADR-0081 Track 2

---

## Why this exists

Two human+agent pairs can grow **parallel universes** in one repo. Without a fresh `fetch`, an agent only sees **stale remote tips** — the operator gets a wrong mental model (e.g. «small concept POC» vs 40+ commits of meaning layer).

Agents **do not run between sessions**. There is no «every N days» cron — only **triggers inside a live inference** when a human opens a chat or starts work.

This scratch defines **when** and **how** an agent produces a one-screen digest before cross-track decisions.

---

## Triggers (run digest when any is true)

| Trigger | Example |
|---------|---------|
| **T1 — Session start, cross-track** | Operator mentions Dima's branch, concept net, merge, cherry-pick, «what's new there» |
| **T2 — Before merge / cherry-pick** | Any work that touches `feat/conceptual-network`, `develop`, or another person's long-lived branch |
| **T3 — Canon conflict** | Two scratches/ADRs disagree; operator asks «what's canonical» |
| **T4 — Operator says «sync»** | Explicit: «fetch and tell me what's on their tip» |

Skip digest when the session is **single-branch, local-only** and no merge is planned.

---

## Agent ritual (one session, ~2 min)

```powershell
cd <repo-root>
git fetch origin
git branch -vv
# for each tracked parallel branch:
git log HEAD..origin/<branch> --oneline -20
git log origin/<branch> -1 --format="%h %ci %an %s"
git diff HEAD...origin/<branch> --stat
```

**Rules:**

1. Always **`git fetch`** before describing remote work — never trust last session's tip.
2. Report **tip hash + date + author + subject** for each parallel branch.
3. Summarize **themes** (3–7 bullets), not every file — link paths for deep dive.
4. State **overlap / collision** with current branch if obvious from `--stat`.
5. Mark **unknown**: «not fetched» / «branch deleted» — do not invent.

---

## Digest template (paste into chat or commit as `tools/_branch_digest_<date>.md`)

```markdown
## Branch digest — <YYYY-MM-DD> — session <optional id>

**Our branch:** `<name>` @ `<short-hash>` — <one line what this track owns>  
**Fetched:** yes/no — <time if known>

### Parallel tracks

#### `origin/<branch>` @ `<hash>` (<date>, <author>)

- **Since our merge-base:** <N> commits
- **Themes:** …
- **Notable paths:** …
- **Touches our canon:** yes/no — <scratch/ADR ids>
- **Merge posture:** independent | cherry-pick candidate | blocked by …

### Collision watch

- …

### Open questions for humans

- …
```

---

## Standing parallel tracks (update when branches change)

| Branch | Owner track | Agent scope (one line) |
|--------|-------------|-------------------------|
| `fix/neumann-free-speech-recovery` | listen Phase B, motor speech, impulse | womb stream, life tick, efferent phonation |
| `origin/feat/conceptual-network` | meaning layer (Dima) | parse → graph → validate → round-trip; situation memory on field |
| `origin/develop` | integration (**concept net merged** @ `1b4e41c`) | merge into our branch before wide integration |

Remove rows when branches merge or retire.

---

## What humans still decide (agents do not)

- Cherry-pick vs full merge vs wait
- Canon: which scratch wins when they conflict
- Pilot order: stream → sleep → rewatch vs concept-net chat demo
- When to stop parallel work and integrate

---

## Tie-in: rewatch gap vs situation memory

| Layer | Branch track | «Seen before?» primitive |
|-------|--------------|----------------------------|
| Sensory video | listen / womb | **open** — familiarity, retrieve-not-re-ingest ([rewatch design TBD](CASA-scratch-listen-wire-gap-v1.md)) |
| Parsed text situation | `feat/conceptual-network` | `situation_memory.seen()` + `situation_store` on field |

Cross-link at design time only — not merged in code yet.

---

## Anti-patterns

- Describing remote branches from **memory of a past chat** without fetch
- Calendar reminders agents cannot execute
- One mega-merge of unrelated tracks «because both green locally»
- Assuming the operator saw the other pair's agent output

---

## Success criterion

Operator can answer in one breath: **«On their tip right now we have X; we have Y; merge means Z.»**  
If the answer is «ого, не знала» — run digest at **next session start** (T1), not «in three days».
