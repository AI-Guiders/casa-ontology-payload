# Lesson 15 — геометрия: слово и фигура

Один кадр = один термин. Micro-moment: visual + русское слово (`math.geom.*`) → sleep.

| frame_id | Слово | Картинка |
|----------|-------|----------|
| `geom-circle` | круг | только контур окружности |
| `geom-square` | квадрат | только квадрат |
| `geom-rectangle` | прямоугольник | только прямоугольник |
| `geom-stroke` | линия | штрих без концов |
| `geom-segment` | отрезок | отрезок с точками на концах |
| `geom-line` | прямая | стрелки с двух сторон |

**Без подписи на JPEG** (вариант A): слово только в math cue moment; probe не читает текст с картинки.

Кадры: `python lessons/visual-cards/tools/build_card_images.py`  
Ingest: `python lab/visual-curriculum/micro-geom/run_micro_geom.py`  
Круг/квадрат (повтор + контраст): `python lab/visual-curriculum/micro-geom/run_geom_round_square_contrast.py`  
Probe: `python lab/visual-curriculum/probe_geom_lex_quiz.py`
