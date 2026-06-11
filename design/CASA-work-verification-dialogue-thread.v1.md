# Verification: partner dialogue thread (working spec)

**Updated:** 2026-06-11  
**Store:** `agents/von-neumann`  
**Command:** `python tools/verify_dialogue_thread.py`  
**Canon:** ADR-0057 (pragmatic class + provenance), scratch emergence §routing vs oracle

## Must pass (real store, fresh dialogue ring)

| # | Partner | Must NOT | Must (class, not surface anchor) |
|---|---------|----------|--------------------------------|
| 1 | Как ты? | — | `how_are_you` + `affect_axes` in provenance; `dialog_hubs` non-empty; affect-family from bind (not template dispatcher) |
| 2 | Хорошо, я тоже не знаю, но он не обязан совпадать | verbatim hub slot only; preamble-only | `mirror_ack` in provenance; reply overlaps partner field («не знаю»/«обязан»/«совпада») |
| 3 | А что ты думаешь про это? | preamble replay; hub-only tail | `ask_thought` in provenance; differs from prior reply; continuer/thread contribution |
| 4 | Спасибо | affect preamble | `thanks` in provenance; thanks-family path (not scripted «не за что» anchor) |

## Architecture norm (not if-oracle)

- `ru.speech_act.partner.*` = **read/bind feature** → `partner_speech_acts` provenance + `speech_act_scoring` zone bias
- `subject.limbic.state` = **read/bind feature** → `affect_axes` provenance + `affect_scoring` reweight; competitive slots skip `clause_1` when security low / repair
- **No** `social_act_compose.py` / `if act == …` efferent templates on hot path
- `subject.dialog.*` = bind-only, never efferent paste
- `dialog.context.focus_recent` = continuer signal from dialogue ring
- Continuer → competitive slot order skips `clause_1`; no hub tail on mirror+uncertainty
- Zones: bind score + budget; efferent from situated thread + ranked `ru.dialog.*` blocks

## Probe checks (script)

1. `partner_speech_acts` matches expected act per turn  
2. `dialog_hubs` present when social reply uses KB material  
3. Anti-replay: banned hub-only strings; preamble not on turns 2–4  
4. Partner-field overlap on mirror turn  
5. `differs_from_prior` on continuer turn  

## Last run

```
2026-06-11 PASS (agents/von-neumann, fresh ring)
Q: Как ты? → Осторожно говорю, что чувствую в диалоге.
Q: mirror → Да — он не обязан совпадать.
Q: А что ты думаешь про это? → Про это — он не обязан совпадать.
Q: Спасибо → Пожалуйста.
Command: python tools/verify_dialogue_thread.py
```
