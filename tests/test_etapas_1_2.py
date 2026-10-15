"""Pruebas etapas 1 y 2. Ejecutar: python -I tests/test_etapas_1_2.py"""
import os, sys, subprocess, tempfile
import numpy as np, cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "grade"))
from etapa1 import *
from etapa2 import estimar, slog3_a_lin, lin_a_slog3

cfg = cargar_config()
lut_path = buscar_lut("Sony S-Log3 to Rec.709")
lut = load_cube(lut_path)
fallos = []


def check(nombre, ok, detalle=""):
    print(("OK    " if ok else "FALLA ") + nombre, detalle)
    if not ok:
        fallos.append(nombre)


# --- Etapa 1: tabla de grises
for v, e in [(0.2056, 0.089), (0.4106, 0.373), (0.5845, 0.691), (0.7491, 0.923)]:
    o = apply_lut(np.array([v] * 3), lut)
    check(f"e1 gris {v}->{e}", np.abs(o - e).max() <= 0.005, f"{o.round(4)}")
    check(f"e1 neutro en {v}", o.max() - o.min() < 0.002, f"spread={o.max() - o.min():.4f}")

# --- Etapa 1: Python vs ffmpeg sobre el mismo frame (se salta sin clip de muestra: samples/orig/C0400.MP4)
video = os.path.join(ROOT, "samples", "orig", "C0400.MP4")
if not os.path.exists(video):
    print("SALTA e1 python vs ffmpeg (no hay clip de muestra)")
else:
    src, _ = decodificar_frame(video, 3.0)
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        cv2.imwrite(a, (src[..., ::-1] * 65535 + 0.5).astype(np.uint16))
        lut_ffmpeg(a, lut_path, b)
        ff = cv2.imread(b, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32) / 65535
    py = aplicar_lut(src, lut)
    dif = np.abs(py - ff)
    check("e1 python vs ffmpeg", dif.mean() < 0.002 and np.percentile(dif, 99.9) < 0.01,
          f"MAE={dif.mean():.5f} p99.9={np.percentile(dif, 99.9):.5f} max={dif.max():.4f}")



# --- Etapa 2: sintética con dominante conocida
def escena(g):
    im = np.full((540, 960, 3), 0.25, np.float32)
    im[100:300, 100:400] = 0.70                       # superficie blanca grande, neutra
    im[350:500, 500:900] = [0.5, 0.2, 0.2]            # objeto rojo
    im[50:150, 600:900] = [0.35, 0.40, 0.55]          # azul apagado
    return np.clip(im * np.array(g, np.float32), 0, 1)


for esp in ("post_lut", "linear"):
    c = dict(cfg); c["normalizacion"] = dict(cfg["normalizacion"], espacio=esp)
    for g in [(1.12, 1.0, 0.88), (0.93, 1.0, 1.15)]:
        if esp == "post_lut":                          # dominante aplicada tras el LUT
            post = escena(g); src = post
        else:                                          # dominante aplicada en luz lineal, antes del LUT
            lin = slog3_a_lin(escena((1, 1, 1))) * np.array(g)
            src = lin_a_slog3(lin).clip(0, 1).astype(np.float32); post = aplicar_lut(src, lut)
        r, cand, _ = estimar(post, src, c)
        rec = np.array(r["ganancias_post_lut"] if esp == "post_lut" else r["ganancias_linear"])
        prod = rec * np.array(g)
        prod = prod / prod.mean()
        check(f"e2 sintética {esp} {g}", np.abs(prod - 1).max() < 0.01, f"rec*aplicada={prod.round(4)} n={r['n_candidatos']}")

# --- Etapa 2: sin blanco confiable
im = np.zeros((540, 960, 3), np.float32)
im[..., 0] = 0.6; im[..., 1] = 0.1; im[..., 2] = 0.1        # todo rojo saturado
r, _, _ = estimar(im, im, cfg)
check("e2 sin blanco -> revisar y no corregir", (not r["corregir"]) and r["ganancias"] == [1.0, 1.0, 1.0] and "sin_blanco_confiable" in r["banderas"], str(r["banderas"]))

print("\nRESULTADO:", "todo OK" if not fallos else f"{len(fallos)} fallos: {fallos}")
sys.exit(1 if fallos else 0)
