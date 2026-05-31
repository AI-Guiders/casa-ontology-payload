# Critic v0 — validate после Predict

**Статус:** design stub (после Predictor v0.5a)  
**Дата:** 2026-05-30  
**Родитель:** [`understanding-contract.md`](understanding-contract.md), [`predictor.md`](predictor.md)

---

## Одна строка

**Critic** — сравнивает `Prediction` с observation (учитель, held-out, internal verify) и возвращает **pass | fail | provisional**; **без pass — нет Extract и нет train `NCA_rule`**.

Не LLM. Operational checks + match/normalize.

---

## API (planned)

```python
# tools/critic.py

def critic_validate(
    prediction: dict,
    *,
    observation: str | None = None,
    expect: str | None = None,
    state: dict | None = None,
    checks: list[str] | None = None,
) -> dict:
    """Returns { verdict, score, checks: [{name, pass, detail}], unit_candidate }."""
```

| verdict | Действие |
|---------|----------|
| **pass** | `UnderstandingUnit` candidate → Extract queue |
| **fail** | surprise event; CEN `clarify` (v1.3); **no** NCA_rule train |
| **provisional** | hippo with TTL; no LTM promote |

---

## Checks v0 (minimal)

| check | pass |
|-------|------|
| **match** | normalize(hypothesis) == normalize(expect or observation) |
| **confidence** | `prediction.confidence >= theta` or explicit low flagged |
| **verify_internal** | для segment: `verify_segment(hyp)["ok"]` |

v1+: coherence digest, coverage, boundary — см. understanding-contract § operational checks.

---

## Bench

`bench_predict.py` вызывает predict + critic_validate; pass rate = UC v0.5 metric.

---

## Sleep gate

```text
critic_validate → pass only →
  understand_extract(unit)
  sleep merge ltm
  train nca/rules/<rule_id>/   # v1.4
```
