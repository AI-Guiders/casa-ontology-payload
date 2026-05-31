# en-general-v0 — EN frequency headwords

**Канон:** [hermitdave/FrequencyWords en_50k](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles-derived, MIT).

```bash
python tools/fetch_en_frequency_headwords_v0.py
python tools/build_lexicon_usage_axes_v0.py --corpus en-general
python tools/build_lexicon_usage_axes_v0.py --corpus en-general \
  --copy-to-store lab/agent-stores/sss-en-folk-v0
```

Sidecar: `frequency.ipm.v1.jsonl` → `lexicon_axes.v0.jsonl` (ipm, rank, `usage_band`, `active_for_t9`).

BiT9 linked boot merges RU DetCorpus + EN OpenSubtitles axes into `state["lexicon_axes"]`.
