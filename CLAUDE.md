# colorear-plano — instrucciones para Claude

Este repo colorea planos Sony S-Log3 al look de Cris (OneScreen). Cuando el usuario te pase este repo (o su link), o un plano para colorear:

1. **Instala** (una sola vez por equipo), si no está hecho:
   - `git clone <link>` y entra a la carpeta (si aún no estás en ella).
   - `pip install -r grade/requirements.txt`
   - Verifica `ffmpeg -version`; si no existe, instálalo o dile al usuario cómo.
   - `python instalar.py` — copia la skill `colorear-plano` a `~/.claude/skills/` para que funcione desde **cualquier** carpeta.
2. **Carga la skill `colorear-plano`** (`.claude/skills/colorear-plano/SKILL.md`) y síguela al pie de la letra. Es el procedimiento completo: cómo correr, qué revisar antes de entregar y las trampas conocidas.
3. Resumen mínimo: `python -I grade/pipeline.py "<clip absoluto>" --sufijo graded` y, para la versión sin balance de blancos, `--fuerza 0 --sufijo graded_ambiente`. Entrega ambas, mira el `contact_sheet.png` antes de enviar y no cambies parámetros calibrados sin que lo pidan.

Reglas: no subas video, frames de clientes ni credenciales a este repo (el `.gitignore` ya excluye `samples/` y `out/`).
