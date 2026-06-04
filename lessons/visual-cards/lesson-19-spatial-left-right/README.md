# lesson-19-spatial-left-right

После S3 (длина): те же два отрезка **A** / **B**, **одинаковая длина**, разный сдвиг по горизонтали.

| frame | vis | meta surface |
|-------|-----|--------------|
| `geom-segments-a-left` | A левее B | «левее», **«слева»** → `lang.meta.spatial.leftOf` |
| `geom-segments-a-right` | A правее B | «правее», **«справа»** → `lang.meta.spatial.rightOf` |

Vis: **одна горизонталь** (lum 2D — см. канон). Synonym ingest: `run_meta_spatial_synonyms_pure.py`.

Не смешивать с compare длины (S3) и не reuse surface «длиннее/короче».

Канон: [CASA-compare-greater-less-v1.md](../../../design/CASA-compare-greater-less-v1.md) · S3b.
