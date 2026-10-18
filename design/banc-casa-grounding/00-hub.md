# BANC × CASA — серия grounding design docs

**Status:** hub (series contract)  
**Date:** 2026-09-19  
**project-id:** `ca-substrate-agent`  
**Data:** `D:\Experiments\casa-data\connectomes\` (BANC v888, MCNS v1.0, FAFB v783)  
**KB note:** `agent-notes/.../note-casa-control-zone-banc-grounding.md`  
**Zones SSOT:** [CASA-ADR-0061](../CASA-ADR-0061-intelligence-zones.md) · [zone-prism-map.v1.json](../zone-prism-map.v1.json)

---

## Зачем

У нас есть **полный чертёж** CNS дрозофилы. CASA уже построила zones/prisms **сама**. Задача серии: по **каждой** нашей подсистеме прочитать природные решения (структура, bottlenecks, cascades, NT) и зафиксировать:

1. **rhyme** — что уже совпадает с BANC/MCNS  
2. **gap** — где мы выдумали иначе / слабее  
3. **port** — что взять в ADR/код (не photocopy 188k нейронов)  
4. **probe** — как проверить на поле

**Не делаем:** эмулятор мухи, вшивку в LLM, «CS лучше про».  
**Делаем:** structural grounding → denser CASA.

---

## Метод (одинаковый на каждый doc)

| Шаг | Что |
|-----|-----|
| 1. CASA surface | zone ADR + prisms/lattices/bridges из map |
| 2. BANC slice | `super_class` / `region` / `cell_class` / NT / betweenness / edgelist subgraph |
| 3. Motifs | afferent→…→efferent; hubs; sparse vs dense; dimorphism |
| 4. Dynamics prior | cascade depth, bottleneck fraction (если применимо) |
| 5. Design delta | таблица rhyme / gap / port / probe |
| 6. ADR link | pointer обратно в zone ADR или follow-up ADR |

**Fixture rule:** subgraph ≤ 10⁴ узлов; freeze JSON в `tools/fixtures/banc_*.json` для CI.

---

## Серия документов (deliverables)

Все файлы в этом каталоге. Порядок = dependency (executive + perceptual + memory сначала).

| # | Doc | CASA zone / organ | BANC / MCNS anchor | Priority |
|---|-----|-------------------|--------------------|----------|
| **00** | `00-hub.md` (этот) | — | — | ✅ |
| **01** | [`01-executive-control.md`](01-executive-control.md) | executive · ADR-0010 · `prism_control` | A/D neck, betweenness, DN→motor, cascade | **P0** ✅ |
| **02** | [`02-perceptual.md`](02-perceptual.md) | perceptual · ADR-0063 | sensory, visual_projection, optic_lobe, ORN/photoreceptors | **P0** ✅ |
| **03** | [`03-memory-hippo.md`](03-memory-hippo.md) | memory · ADR-0068 / 0088 · MB | mushroom body, Kenyon, MBON, dopamine PPL→MB | **P0** ✅ |
| **04** | [`04-neuromodulator.md`](04-neuromodulator.md) | neuromodulator · ADR-0066 | DA/5HT/OA/ACh/GABA predictions, gain bus | **P1** ✅ |
| **05** | [`05-emotional-limbic.md`](05-emotional-limbic.md) | emotional · ADR-0060 / 0058 | dimorphic hotspots, courtship/aggression circuits, value-like | **P1** ✅ |
| **06** | [`06-metabolic-sleep.md`](06-metabolic-sleep.md) | metabolic · ADR-0064 | sleep pressure analogs, fatigue (best-effort; fly sleep lit + hubs) | **P2** ✅ |
| **07** | [`07-motor-efferent.md`](07-motor-efferent.md) | executive tip / FSR motor | motor, descending→muscle, VNC intrinsic | **P0** ✅ |
| **08** | [`08-spatial-navigation.md`](08-spatial-navigation.md) | spatial · ADR-0061 | central complex, CX, heading | **P1** ✅ |
| **09** | [`09-social-partner.md`](09-social-partner.md) | social · partner wire | P1 sensory social, dimorphic, courtship song neurons | **P2** ✅ |
| **10** | [`10-genetic-innate.md`](10-genetic-innate.md) | genetic · ADR-0062 / 0059 | hemilineage, cell_type innate catalog, fruitless/dsx (MCNS) | **P1** ✅ |
| **11** | [`11-defense-survival.md`](11-defense-survival.md) | defense · ADR-0074/0076 | escape, threat, giant fiber, aversive | **P2** ✅ |
| **12** | [`12-linguistic-logical.md`](12-linguistic-logical.md) | linguistic / logical | **honest: no fly language** — only metaphor (compose chains, schema motifs) or *out of scope* | **P3** ✅ |
| **13** | [`13-character-slow.md`](13-character-slow.md) | character · ADR-0071 | slow bias / isomorphic periphery vs dimorphic higher | **P2** ✅ |
| **99** | [`99-synthesis-port-map.md`](99-synthesis-port-map.md) | cross-zone | unified port table → roadmap ADRs | ✅ |

**Linguistic/logical (12):** не натягивать. Либо явный «нет биологического аналога → наши данные», либо только graph-compose metaphors.

---

## Карта zone → BANC (cheat sheet)

| CASA (`0061`) | Fly structural prior |
|---------------|----------------------|
| executive | A/D, FPN-like higher centers, predict≈cascade, DAN≈bottleneck sparse |
| perceptual | sensory + VP + optic; fan-out before CB |
| memory | MB (episodic-like), consolidate≈dopamine teach; hippo≠copy |
| neuromodulator | NT classes as gain channels |
| emotional / value | dimorphic + neuromod + MB valence |
| motor | DN + motor + VNC |
| spatial | central complex |
| social | dimorphic / courtship (♂ MCNS critical) |
| genetic | cell_type / hemilineage catalog @ T=0 |
| defense | escape / aversive pathways |
| metabolic | sleep/arousal literature + network load proxies |
| linguistic / logical | **own data**; fly = organization lessons only |

---

## Template каждого leaf doc

```markdown
# BANC grounding: <Zone>
**Status:** draft | **CASA:** ADR-00xx | **Data:** BANC v888 [+ MCNS]

## 1. CASA surface (what we built)
## 2. BANC slice (queries + numbers)
## 3. Motifs (diagram)
## 4. Rhyme / Gap / Port
## 5. Probes
## 6. Follow-up ADR / code
```

---

## Anti-patterns (series-wide)

| ❌ | ✅ |
|----|-----|
| Один огромный ADR на всё | серия leaf docs + `99-synthesis` |
| «Муха умеет язык» | linguistic = own curriculum |
| Copy 188k into field | motifs + grow-to-spec |
| Только executive | **все** zones из 0061 |
| Tier-2 EM first | tier-1 tables достаточно для P0–P1 |

---

## Next

1. ~~Серия 01–13 + 99~~ — **complete** 2026-09-19.  
2. Operator discussion: см. [99-synthesis §8](99-synthesis-port-map.md#8-discussion-agenda-for-operator-review).  
3. Implementation phase: fixtures + `bench_banc_cascade_vs_predict.py` + lab ADR addenda.

Hub принят оператором 2026-09-19 («по всем подсистемам… серия доков в design»).
