# colorear-plano

Pipeline automático que colorea planos **Sony S-Log3** al look de Cris (OneScreen): conversión a Rec.709 → balance de blancos → luz → look (enfriamiento, Kodak 2383, HSL inverso, viñeta).

## Para usarlo con Claude Code (lo más fácil)
Abre Claude Code y dile:

> Clona `<link de este repo>`, instálalo y úsalo para colorear este plano: `<ruta del clip>`

Claude leerá `CLAUDE.md`, instalará las dependencias, copiará la skill y colorea el plano. No hay que hacer nada más.

## A mano
```bash
git clone <link> && cd colorear-plano
pip install -r grade/requirements.txt      # numpy, opencv-python, pyyaml, scipy
python instalar.py                         # opcional: skill disponible desde cualquier carpeta
python -I grade/pipeline.py "C:/ruta/clip.MP4" --sufijo graded
python -I grade/pipeline.py "C:/ruta/clip.MP4" --fuerza 0 --sufijo graded_ambiente
```
Requiere `ffmpeg` y `ffprobe` en el PATH. Salida en `samples/graded/` y reportes/imágenes de comparación en `out/pipeline/`.

Dos versiones por plano: `_graded` (balance de blancos al 100 %) y `_graded_ambiente` (conserva el ambiente de la luz). Revisa siempre el `contact_sheet.png`.

## Estado y límites
- Probado en Windows. Material esperado: Sony A7III, S-Log3 / S-Gamut3.Cine, 8 bits.
- Sin decidir: si el balance de blancos debe ir al 100 % o con ambiente. La luz se calibró con una sola toma de referencia; la viñeta solo en vertical.
- Los LUTs de `luts/` son de terceros (FestivalLuts y Glenderaterra MOD): úsalos según sus licencias.
- Detalles técnicos y trampas conocidas: `.claude/skills/colorear-plano/SKILL.md`. Parámetros: `config/estilo.yaml`.
