# lesson-18-segment-compare

Два отрезка **A** (сверху) и **B** (снизу), общее начало слева.

| frame | vis | meta surface (S3) |
|-------|-----|-------------------|
| `geom-segments-equal` | A = B | «равны» → `lang.meta.compare.equal` |
| `geom-segments-a-longer` | A длиннее | «длиннее» → `lang.meta.compare.greater` |
| `geom-segments-a-shorter` | A короче | «короче» → `lang.meta.compare.less` |

**Не смешивать** с «больше/меньше» на numberline — отдельный runner `run_meta_compare_segments_pure.py`.

Канон: [CASA-compare-greater-less-v1.md](../../../design/CASA-compare-greater-less-v1.md) · S3.
