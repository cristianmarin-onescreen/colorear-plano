---
name: colorear-plano
description: Colorea (gradúa) planos Sony S-Log3 al look de Cris (OneScreen) con el pipeline automático de este repo. Úsalo siempre que te pasen un plano/clip grabado en S-Log3 (Sony A7III u otra Sony) y pidan color, graduación, "colorear", "pasar a Rec.709" o "el look de Cris"; también cuando un proyecto de Hyperframes use planos S-Log3 que deban entrar ya graduados.
---

# Colorear un plano al look de Cris

La raíz del repo es la carpeta que contiene `grade/` y `config/`. Todo el código vive en `grade/`, los parámetros en `config/estilo.yaml`. **No reescribas el pipeline ni cambies parámetros calibrados sin que el usuario lo pida.** Si algo no es medible aquí, dilo.

## Primera vez en este equipo
1. `python -I grade/pipeline.py --help` debe responder. Si falta algo: `pip install -r grade/requirements.txt`.
2. `ffmpeg` y `ffprobe` deben estar en el PATH (`ffmpeg -version`). Si no, instálalos (winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg) o pídele al usuario que lo haga.
3. `luts/` debe tener los dos `.cube` (se identifican por cabecera, no por nombre). Si faltan, algo falló al clonar: avisa al usuario.
4. Prueba rápida sin video: `python -I tests/test_etapas_1_2.py` (el chequeo Python vs ffmpeg se salta sin clip de muestra).

## Qué hace (orden fijo)
1. **Conversión:** LUT `Sony S-Log3 to Rec.709` → RGB float, rango completo.
2. **Temperatura neutra:** detecta el blanco en superficies extensas (no brillos, no fuentes de luz, no piel) y lo lleva a neutro. `normalizacion.fuerza`: 1.0 = neutro total, 0 = conserva el ambiente.
3. **Luz:** curva por canal (PCHIP) anclada en los percentiles de la toma (negros ≈ 0.08, blancos ≈ 0.95; las fuentes de luz > 0.95 no fijan el techo).
4. **Look:** enfriamiento (R×0.945, B×1.055) → LUT Kodak 2383 al 50 % → HSL inverso (protege rojos/piel, enfría el resto) → viñeta (`salida = entrada^p(r)`, circular).

Las etapas 1-4c se hornean en un `.cube` de 65³ por toma y ffmpeg lo aplica (`lut3d` tetraédrico). La viñeta se aplica en Python cuadro a cuadro.

## Cómo ejecutarlo
```bash
# Versión estándar (balance de blancos al 100 %) -> samples/graded/<toma>_graded.mp4
python -I grade/pipeline.py "ruta/absoluta/clip.MP4" --sufijo graded
# Versión "ambiente" (sin balance de blancos)   -> samples/graded/<toma>_graded_ambiente.mp4
python -I grade/pipeline.py "ruta/absoluta/clip.MP4" --fuerza 0 --sufijo graded_ambiente
# Solo cuadros de prueba (rápido, sin video)
python -I grade/pipeline.py "ruta/absoluta/clip.MP4" --solo-frames --work "<carpeta temporal>"
```
Varias tomas: pasa varias rutas. `--out` cambia la carpeta de salida. Las salidas van a `<raíz>/samples/graded` y `<raíz>/out/pipeline` sin importar el directorio actual.

- Un 4K de 144 cuadros tarda ~2.5 min: **córrelo en segundo plano**. Si el disco está lleno, usa `--out` en otro.
- Cada toma deja en `out/pipeline/<sufijo>/<toma>/`: `report.json` (ganancias, percentiles, banderas), `<toma>.cube`, `antes_etapa1.png`, `despues.png`; y un `contact_sheet.png`.

## Antes de entregar (siempre)
1. Lee `report.json`: la bandera `revisar_balance_de_blancos` significa que el color queda sin corregir (válido, pero díselo al usuario); `ganancias_inestables_entre_frames` = toma con luz cambiante.
2. **Mira el `contact_sheet.png`** (antes/después). Ningún número sustituye ver la imagen: busca tomas oscuras o apagadas, dominantes, piel quemada o verdosa.
3. Entrega **las dos versiones** (estándar y ambiente) salvo que el usuario ya haya elegido. En la toma 02 de referencia de Cris, "ambiente" se acercó más a su criterio (MAE 0.0285 vs 0.050); en la 01 coinciden. Sigue **sin decidirse** cuál es la regla de Cris: no lo afirmes.
4. No cambies el código para "arreglar" un plano concreto. Si un plano sale mal, reporta qué viste y propón el cambio.

## Con Hyperframes
Hyperframes (HTML + GSAP + Puppeteer/FFmpeg) no debe graduar: **gradúa el plano antes** con este pipeline y usa el `*_graded.mp4` como `<video>` de la composición. Si el clip ya viene graduado, no lo vuelvas a pasar.

## Trampas conocidas (no las redescubras)
- Los MP4 de la A7III vienen `yuvj420p`, rango completo, **sin etiquetas de color**; se asume matriz bt709. `rango: limited` no tiene efecto con `yuvj` (ffmpeg lo ignora).
- Hay clips grabados con la cámara girada 90° sin metadato de rotación: **no se giran**, solo se colorea.
- Rutas con tildes: `cv2.imread` falla; usa `cv2.imdecode(np.fromfile(...))`.
- `lut3d` en Windows no acepta rutas con `:`; el código copia el `.cube` junto al trabajo y usa ruta relativa con `cwd`.
- Python vs ffmpeg en la etapa 1: error medio 0.0006 pero con puntos sueltos hasta 0.0975 (sin investigar).
- Viñeta calibrada solo en vertical 1080×1920; en horizontales no está validada y oscurece los laterales con la misma regla.
- `max_shift` (0.35) y `max_estiramiento` (1.5) son provisionales; la etapa 4c (HSL) queda en MAE 0.0070 (meta 0.006); la luz se calibró con una sola toma.
- Material de 8 bits: no subas más el contraste (ruido y bandas en sombras).
- Probado solo en Windows con Python 3 + ffmpeg reciente.
