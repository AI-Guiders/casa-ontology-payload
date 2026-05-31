# sss-ru-general-v0

**Locale:** ru | **Tier:** general | **Corpus:** ru-general-v0

L2 shards: `L2_word_*`. Cold add: `lexicon_cold_ingest_v0.py`.

Train NCA (CUDA):
```bash
python tools/train_sss_nca_shards_v0.py --store-dir lab/agent-stores/sss-ru-general-v0 --layer all --device cuda
python tools/nca_registry_v0.py --sync-registry --store-dir lab/agent-stores/sss-ru-general-v0
```
