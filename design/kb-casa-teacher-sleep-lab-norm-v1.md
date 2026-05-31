# KB CASA: teacher / sleep lab norm (v1)

**Date:** 2026-05-31  
**Status:** canon (CASA operational; agent-notes primary)  
**KB path:** `work/projects/door-to-singularity/ca-substrate-agent/kb-casa-teacher-sleep-lab-norm-v1.md`  
**Spec:** [`teacher-correction-protocol.md`](teacher-correction-protocol.md)  
**Machine cards:** `lab/kb/teacher_correction_cards.v1.json`

---

## Граница доменов

**Педагогика** (детское усвоение языка, Vygotsky, Snow, …) — **отдельный мир**. К CASA **не относится напрямую**: не спецификация, не обоснование bench, не «empirical canon» для агента.

**CASA** — инженерный контракт: `surface` → **critic** (ось ошибки) → **teacher** → Extract → **sleep**; `correction_kind`, scene, T9 fork, hippo episodes. Нормы ниже — **только** из контракта и lab (prefix ambiguity, mixed script, entity hub ≠ teacher).

Сравнение с «как ребёнок» в [`language-acquisition-loop.md`](language-acquisition-loop.md) — **метафора north star**, не импорт теории. Evidence (human L1, отдельный мир): agent-notes `worlds/cognition-language-acquisition/kb-language-acquisition-scientific-evidence-v1.md` (+ per-paper evidence cards).

---

## Agent preflight (перед sleep cue / teacher bench)

Перед `append_episode` / sleep strengthen по **surface → correct**:

1. **Ось ошибки** — script | phonotactic | prefix_incomplete | lexical | morph | ortho; оси **не смешивать**.
2. **Commitment:** utterance = короткий **prefix** без scene → **запрещён** oracle одной леммы (`correct: корова` на `кор` — **FAIL**).
3. **POS:** коровий / короб / кор — разные targets; без scene teacher **не выбирает**.
4. **Entity hub ≠ teacher:** `entity.cow ↔ корова` — cold L3; **не** license «корова» на каждый `кор*`.
5. **Sleep merge:** только с `correction_kind`; rule-only на mixed script **без** lemma strengthen.

Сомнение → [`teacher-correction-protocol.md`](teacher-correction-protocol.md), не «угадай по здравому смыслу».

---

## Prefix ambiguity (lab case: `кор`)

**Lexicon:** на `кор*` — кор, кора, корм, короб, коробка, коровий, корова, король, …

| Input | Запрещено | Допустимо (CASA) |
|-------|-----------|------------------|
| prefix `кор` | oracle lemma | `wait_prefix`; T9 fork; `lexical_ask` **с** scene |
| babble `кoro` mixed | lexical correct | `script_rule` → `append_rule_episode` |
| `коров` → adj intent | `корова` | `morph_surface` + scene («коровий суп») |
| committed word, bad ortho | — | `ortho_surface` |

**T9:** короткий prefix + score bias ≠ intent; teacher **не** collapse fork в одну лемму.

---

## Фазы (CASA, не возраст ребёнка)

См. [`infancy-corpus-phases.md`](infancy-corpus-phases.md):

```text
0 wiring → 1 phonotactics → 2 listen mass → 3 surface→correct → 4 sleep → 5 T9 prod
```

Teacher-heavy: фазы 3–4. Фаза 2 — ingest без teacher quiz на токен.

---

## Lab anti-patterns (release blockers)

| Anti-pattern | Почему (CASA) |
|--------------|---------------|
| Oracle lemma на bare prefix | Схлопывает T9 fork; ложный hippo/sleep |
| Sleep без `correction_kind` | UC artifact, невоспроизводимо |
| Entity ingest как teacher oracle | Смешение L3 batch и episodic Extract |
| `teacher_two_phase` rule + random noun | Две оси в одном cue |
| Импорт педагогики в spec/bench | Чужой домен маскирует дыры контракта |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-31 | v1: CASA-only lab norm; pedagogy вынесена во external bib |
