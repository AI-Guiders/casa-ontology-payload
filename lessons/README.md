# Lessons (curriculum)

**Not lab.** Pedagogy lives here: class plans, lesson bundles, ingest payloads for agent **events** — not agent memory roots.

| Term | Meaning |
|------|---------|
| **class** | Course / track (e.g. `math-palochki`) |
| **lesson** | One session (`lesson-01`, …) — a single teaching episode |
| **agent store** | `agents/<id>/` — own experience after listen/sleep (ADR-0021) |

Legacy dev corpus and CI snapshots remain under `lab/` until migrated (TECH-DEBT L1).

```text
lessons/
  <class-id>/
    README.md           # syllabus
    lesson-NN-<slug>/   # one session (plan + optional .payload.json)
```

Ingest: lesson bundle → event on agent (e.g. `agents/von-neumann/`); the folder is curriculum source, not a second brain.
