# ru-general — частотный словарь (general RU)

**Канон:** [DetCorpus 50k lemmas](https://github.com/Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children) (CC0-1.0), не сказки Афанасьева.

**Афан не в prod** — lab/archaic (`sss-ru-lexicon`). Оси: `design/lexicon-usage-axes.md`.

```bash
python tools/build_lexicon_usage_axes.py --corpus ru-general
# → lexicon_axes.jsonl (era, usage_band, active_for_t9)
```

## Сборка headwords

```bash
python scripts/download_corpora.py
# or: python tools/fetch_ru_frequency_headwords.py
# → headwords.v1.txt + frequency.ipm.v1.jsonl (gitignored, not in repo)
```

## Store + GPU

```bash
python tools/init_lexicon_store.py --corpus-id ru-general
python tools/remigrate_l2_lex.py --store-dir lab/agent-stores/sss-ru-general
python tools/train_memory_nca_shards.py --store-dir lab/agent-stores/sss-ru-general --layer all --device cuda
```

Объяснение понятий частоты (sleep / L3): `lab/kb/kb-lexicon-frequency-ru-v1.json`.
