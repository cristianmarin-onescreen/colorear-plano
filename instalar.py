"""Instala la skill `colorear-plano` a nivel de usuario (~/.claude/skills) apuntando a este repo.

Uso: python instalar.py
Después, Claude Code puede colorear planos desde cualquier carpeta.
"""
import os, shutil, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(RAIZ, ".claude", "skills", "colorear-plano", "SKILL.md")
DESTINO_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", "colorear-plano")


def main():
    problemas = []
    for mod in ("numpy", "cv2", "yaml", "scipy"):
        try:
            __import__(mod)
        except ImportError:
            problemas.append(f"falta el paquete Python '{mod}' -> pip install -r grade/requirements.txt")
    for exe in ("ffmpeg", "ffprobe"):
        if shutil.which(exe) is None:
            problemas.append(f"falta '{exe}' en el PATH")
    if len(os.listdir(os.path.join(RAIZ, "luts"))) < 2:
        problemas.append("luts/ no tiene los dos .cube")

    texto = open(ORIGEN, encoding="utf-8").read()
    texto += (f"\n\n## Ubicación en este equipo\nRaíz del repo (donde están `grade/` y `config/`): `{RAIZ}`\n"
              "Ejecuta los comandos desde esa carpeta o usa rutas absolutas a `grade/pipeline.py`.\n")
    os.makedirs(DESTINO_DIR, exist_ok=True)
    with open(os.path.join(DESTINO_DIR, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    print("Skill instalada en", DESTINO_DIR)
    if problemas:
        print("\nPENDIENTE:")
        for p in problemas:
            print(" -", p)
        sys.exit(1)
    print("Todo listo: dependencias y LUTs encontrados.")


if __name__ == "__main__":
    main()
