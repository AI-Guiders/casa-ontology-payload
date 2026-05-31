# ru-general-v0 — частотный словарь (general RU)

**Канон:** [DetCorpus 50k lemmas](https://github.com/Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children) (CC0-1.0), не сказки Афанасьева.

**Афан не в prod** — lab/archaic (`sss-ru-lexicon-v0`). Оси: `design/lexicon-usage-axes-v0.md`.

```bash
python tools/build_lexicon_usage_axes_v0.py --corpus ru-general
# → lexicon_axes.v0.jsonl (era, usage_band, active_for_t9)
```

## Сборка headwords

```bash
python scripts/download_corpora.py
# or: python tools/fetch_ru_frequency_headwords_v0.py
# → headwords.v1.txt + frequency.ipm.v1.jsonl (gitignored, not in repo)
```

## Store + GPU

```bash
python tools/init_lexicon_store_v0.py --corpus-id ru-general
python tools/remigrate_l2_lex_v0.py --store-dir lab/agent-stores/sss-ru-general-v0
python tools/train_sss_nca_shards_v0.py --store-dir lab/agent-stores/sss-ru-general-v0 --layer all --device cuda
```

Объяснение понятий частоты (sleep / L3): `lab/kb/kb-lexicon-frequency-ru-v1.json`.
