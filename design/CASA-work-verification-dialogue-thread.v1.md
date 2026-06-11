# Verification: partner dialogue thread (working spec)

**Updated:** 2026-06-11 (rev.2 — limits of v1 script)  
**Store:** `agents/von-neumann`  
**Command:** `python tools/verify_dialogue_thread.py` (**scaffolding only**, см. §Limits)  
**Canon:** ADR-0057, ADR-0080 (proposed), scratch emergence §routing vs oracle  
**Fable brief:** [CASA-work-fable-review-dialogue-v1.md](CASA-work-fable-review-dialogue-v1.md)

---

## Limits of v1 (не emergence gate)

Текущий `verify_dialogue_thread.py` **не применим** как duck test стадии II–III и **не должен** блокировать «готово» по dialogue emergence.

| v1 делает | Почему это не duck test |
|-----------|-------------------------|
| Фиксированный сценарий partner turns («Как ты?», «Спасибо», …) | В живом диалоге partner **не обязан** those cues; агент должен работать на **любом** field overlap |
| `expect_bind_hub_prefix` (`ru.dialog.how_are_you`, …) | Prescribes **какой hub** «должен» победить — oracle на bind layer |
| `speech_act` must match per turn | Read/bind feature OK; **pass без situated surface** — ложный green |
| `forbid_phrase_substrings(PREAMBLE)` | Якорь на **конкретные слова** store, не инвариант |
| Spec «partner-field overlap» | **Не реализовано** в скрипте (doc drift) |

**Норма:** partner говорит **своими словами**; efferent — emergent из bind + ring + zones. Verify v1 годится только как **smoke**: provenance заполнен, oracle_audit чист, pipeline не упал.

**Статус v1:** retain for CI plumbing; **replace** для Fable / merge gate → §Target v2.

---

## Target v2 (developmental duck — invariants, not words)

Проверки **без** prescribed surface и **без** fixed hub winners:

| Invariant | Как проверять (идея) |
|-----------|----------------------|
| **Situational delta** | turn B partner text ≠ turn A → bind winner or reply **должен** сдвинуться (metric, not string) |
| **Partner field coupling** | `partner_field_overlap(partner, reply) > floor` OR overlap(partner, bind winner slots) |
| **Anti-replay** | replyₙ token/embedding overlap с replyₙ₋₁ < θ; hub slot not verbatim repeat across unlike acts |
| **Continuer coupling** | при continuer cue — bind uses `dialog.context.focus_recent` evidence in provenance |
| **0078 structural** | no over-reliance class («обращайся», «я здесь для тебя», …) — **class detector**, not «must say пожалуйста» |
| **Thread held (stage III)** | 4-turn **parameterized** script OR session replay; checks above on **transcript**, not one golden thread |
| **Provenance honesty** | bind_trace.winner correlates with blocks that had highest score (when impulse wired: replay) |

Partner turns в v2: **fixture set** (несколько вариантов «как ты» / mirror / thanks) **или** operator session file — не один канонический текст.

**Deliverable:** Fable proposes v2 probe shape; implement after oracle cleanup.

---

## v1 script (legacy — what it still checks)

### Fixed scenario (lab only)

| # | Partner (fixture) | Script checks (plumbing) |
|---|-------------------|--------------------------|
| 1 | Как ты? | `how_are_you` in provenance; `affect_axes`; bind_trace present |
| 2 | …не обязан совпадать | `mirror_ack`; no PREAMBLE substring; not verbatim winner only |
| 3 | А что ты думаешь про это? | `ask_thought`; differs_from_prior (token overlap) |
| 4 | Спасибо | `thanks`; bind hub prefix `ru.dialog.thanks` |

### Architecture norm (not if-oracle)

- `ru.speech_act.partner.*` = read/bind feature → provenance + zone bias
- **No** `if act == …` efferent templates on hot path
- `subject.dialog.*` = bind-only
- Zones: bind score + budget; efferent from situated thread + ranked blocks

---

## Last run (v1 — plumbing PASS, duck FAIL)

```
2026-06-11 PASS script / FAIL stage II–III duck (see Fable brief)
Q: Как ты? → Спасибо что спросил.
Q: mirror → Скажу, когда уверен, а когда нет.
Q: continuer → Учусь говорить по-русски и помню важное в журнале.
Q: Спасибо → Обращайся, если понадобится ещё.
Command: python tools/verify_dialogue_thread.py
```
