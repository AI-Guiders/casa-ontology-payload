# Scratch: цифровая биология — заимствования для CASA (v1)

**Status:** scratch — зафиксировано для обсуждения (не normative)  
**Date:** 2026-06-21  
**Provenance:** диалог оператор (Света) + агент — после ADR-0084 wild donor; «пока не всё поняла, но принимаю, потом обсудим»  
**Related:** [CASA-ADR-0062-genetic-zone.md](CASA-ADR-0062-genetic-zone.md), [CASA-ADR-0065-controlled-mutations.md](CASA-ADR-0065-controlled-mutations.md), [CASA-ADR-0072-genetic-weather-cross.md](CASA-ADR-0072-genetic-weather-cross.md), [CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md), KB: `agent-notes/.../note-casa-synthetic-genome-donor-v1.md`, `playbook-casa-levin-biology-bridge-operational-v1.md`, `kb-distill-growing-neural-ca-fundamentals-v1.md`

---

## Зачем этот файл

Краткая **карта заимствований** из цифровой биологии / artificial life — что уже есть в CASA под другими именами, что предложено добавить, что **не** тащить.  
Не ADR: при обсуждении решим, что поднимать в normative docs и что в код.

---

## Уже есть (можно называть явно)

| Цифровая биология | Где у нас |
|-------------------|-----------|
| **Germline vs soma** (геном не переписывается опытом) | ADR-0065: sealed genome vs Track A experiential |
| **Морфогенез из локального правила** | Growing NCA, поле |
| **Регенерация после урона** | NCA training + honesty на recovery |
| **Bioelectric / поле как согласование** | Levin playbook (KB) |
| **Рекомbination / внешняя энтропия** | ADR-0072 weather; ADR-0084 wild donor + `cpu_drng` |
| **«Эpigénome» без смены ДНК** | character zone, trauma cement, WM — опыт меняет экспрессию, не `genome.v1.json` |

---

## Предложено обсудить (приоритет)

### P1 — Phenotype ≠ genotype (Avida, evo-devo)

**Идея:** ценность fork — не «красивый hash», а **поведение @ T=0** в среде (battery), не байты генома.

| Дешёвый шаг | Описание |
|-------------|----------|
| Phenotype battery @ child birth | duck test, metabolic/sleep probe, опционально listen surprise — **не** chat oracle |
| Метрика в lineage | `genome_distance` vs `phenotype_distance` между siblings |

**Связь:** дополняет ADR-0084 honesty gate; wild donor тогда = разные **стартовые фенотипы** при том же species spine.

---

### P2 — Канализация (Waddington, robustness)

**Идея:** малые мутации аллелей → фенотип остаётся **в бассейне вида**, не каждый fork = другая личность.

| Дешёвый шаг | Описание |
|-------------|----------|
| Canalization probe | ±ε по одному allele → N life ticks → limbic/character в коридоре |
| Связь с NCA | perturb → return to attractor (регенерация формы) |

**Связь:** spine + bounds в 0084; Growing NCA fundamentals.

---

### P3 — Горизонтальный перенос / HGT (Tierra, не буквальные паразиты)

**Идея:** обмен **sandbox / lattices / curriculum shards** между агентами AiNet **без** полного genome cross.

| Правило | |
|---------|---|
| ✅ | experiential layers, agent-owned lattices (0062: hash mismatch → reject meta) |
| ❌ | spine, `species_id`, wholesale genome |

**Имя для обсуждения:** `HGT track` — явно отделить от vertical reproduction (0084).

---

### P4 — Red Queen / niche construction (слабая версия)

**Идея:** среда и агент **связаны**: погода/host → другой entropy mix; агент меняет store (listen imprint) → другой контекст следующего fork.

**Не делать:** literal host–parasite / malware-метафора.

**Дешёвый шаг:** fork_tick + entropy bundle привязать к audit trail (уже в 0072/0084 lineage).

---

### P5 — Developmental unroll / «regulatory genome» (GRN)

**Идея:** `genome.v1.json` = **программа развёртки** @ birth (regulatory), не таблица готовых ответов.

**Уже намечено:** один `H_mix` → forgetting + character_topology + zone proportions согласованно (0072/0084 § unroll).

**Для обсуждения:** закрепить термин **regulatory genome** в 0062 glossary.

---

### P6 — Lenia / biomorphes (perceptual prior)

**Идея:** не язык, а **prior на движение/форму** — см. README ca-substrate § Lenia.

**Связь:** listen/motor pilot; отложено до wire-gap закрыт.

---

## Не тащить (или только метафора)

| Идея | Почему |
|------|--------|
| Tierra-parasites буквально | мало пользы, security theater |
| Fitness = reproduction rate | north star — **субъект**, не колония |
| Open-ended evolution «ради сложности» | без kill-criteria → декоративная сложность |
| Полная симуляция клетки | другой масштаб, не CASA |

---

## Сводная схема (для следующего разговора)

```text
cpu_drng + weather     →  wild donor        (энтропия тела + мира)     [0084 ✓ draft]
GRN unroll             →  child @ T=0       (согласованный фенотип)    [0072/0084 ✓ draft]
canalization probe     →  тот же вид        (spine держит)             [P2 —— обсудить]
phenotype battery      →  honesty           (не oracle в чате)         [P1— обсудить]
HGT track              →  AiNet lattices    (обмен без инбридинга)     [P3— обсудить]
epigenome              →  character/WM      (опыт без rewrite genome)  [есть, назвать?]
```

---

## Рекомендованный порядок, когда вернёмся

1. **P1 + P2** — phenotype battery + canalization probe (мало кода, много честности).
2. **P3** — только если AiNet / второй store в горизонте.
3. **P5** — glossary в 0062, без нового кода.
4. **P4, P6** — по необходимости pilot.

---

## Open questions (для обсуждения с оператором)

- [ ] Phenotype battery: минимальный набор probes @ T=0?
- [ ] Canalization: какой ε и какой коридор «тот же вид»?
- [ ] HGT: какие lattice ids разрешены к обмену?
- [ ] Нужен ли отдельный ADR или расширение 0084/0065?
- [ ] Что из списка **не** резонирует — вычеркнуть явно.

---

## Links

- [CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md](CASA-ADR-0084-wild-genome-donor-single-agent-reproduction.md)
- [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md) — параллельный контур (sensory), не смешивать scope
