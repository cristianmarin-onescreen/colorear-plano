"""Etapa 2: temperatura neutra por detección del blanco (sobre la salida de la etapa 1)."""
import argparse, json, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from etapa1 import *

LUMA = np.array([0.2126, 0.7152, 0.0722])


def slog3_a_lin(x):
    x = np.asarray(x, np.float64)
    return np.where(x >= 171.2102946929 / 1023, 10 ** ((x * 1023 - 420) / 261.5) * 0.19 - 0.01,
                    (x * 1023 - 95) * 0.01125 / (171.2102946929 - 95))


def lin_a_slog3(y):
    y = np.asarray(y, np.float64)
    return np.where(y >= 0.01125, (420 + np.log10((np.maximum(y, 1e-9) + 0.01) / 0.19) * 261.5) / 1023,
                    (y * (171.2102946929 - 95) / 0.01125 + 95) / 1023)


def candidatos(img, cfg):
    """img: salida etapa 1 (float 0-1). Superficies extensas, claras y poco saturadas; no puntos ni fuentes."""
    n = cfg["normalizacion"]
    Y = img @ LUMA
    mx, mn = img.max(-1), img.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    excl = dict(recortado=mx >= n["clip_canal"], fuente=Y > n["excluir_sobre"], saturado=sat > n["sat_max"],
                oscuro=Y < n["luminancia_min"])
    valido = ~(excl["recortado"] | excl["fuente"] | excl["saturado"] | excl["oscuro"])
    k = max(3, int(n["abrir_frac"] * img.shape[1]) | 1)                 # solo sobreviven regiones más anchas que k px
    ab = cv2.morphologyEx(valido.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(bool)
    Yf = cv2.GaussianBlur(Y.astype(np.float32), (0, 0), max(1.0, k / 4))
    if ab.sum() == 0:
        return np.zeros_like(ab), excl, 0.0
    umbral = float(np.percentile(Yf[ab], 100 - n["percentil_blancos"]))
    cand = ab & (Yf >= umbral)
    kk, lab, st, _ = cv2.connectedComponentsWithStats(cand.astype(np.uint8), connectivity=8)
    amin = max(4, int(n["area_min_frac"] * cand.size))
    keep = np.zeros(kk, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= amin
    return keep[lab], excl, umbral


def estimar(post, src, cfg):
    """post: frame tras LUT, src: frame S-Log3 decodificado (mismo tamaño)."""
    n = cfg["normalizacion"]
    cand, excl, umbral = candidatos(post, cfg)
    r = dict(n_candidatos=int(cand.sum()), umbral_luminancia=umbral, banderas=[], corregir=False)
    if r["n_candidatos"] < n["min_candidatos"]:
        r.update(banderas=["sin_blanco_confiable"], blanco_estimado=None, ganancias=[1.0, 1.0, 1.0], confianza=0.0)
        return r, cand, excl
    px = post[cand]
    w = np.median(px, axis=0)
    rb = px[:, 0] - px[:, 2]
    disp = float(np.median(np.abs(rb - np.median(rb))))
    r.update(blanco_estimado=w.tolist(), dispersion_r_menos_b=disp, r_menos_b_blanco=float(w[0] - w[2]))
    g_post = (w @ LUMA) / w                                    # blanco -> gris de su misma luminancia
    wl = np.median(slog3_a_lin(src[cand]), axis=0)             # mismo blanco, en luz lineal (antes del LUT)
    g_lin = (wl @ LUMA) / wl
    r.update(ganancias_post_lut=g_post.tolist(), ganancias_linear=g_lin.tolist())
    g = g_post if n["espacio"] == "post_lut" else g_lin
    g = 1 + n["fuerza"] * (g - 1)
    r["ganancias"] = g.tolist()
    r["shift_max"] = float(np.abs(g - 1).max())
    r["confianza"] = float(np.clip(1 - disp / n["dispersion_max"], 0, 1) * min(1, r["n_candidatos"] / (4 * n["min_candidatos"])))
    if disp > n["dispersion_max"]:
        r["banderas"].append("candidatos_dispersos")
    if r["shift_max"] > n["max_shift"]:
        r["banderas"].append("excede_max_shift")
    r["corregir"] = not r["banderas"]
    if not r["corregir"]:
        r["ganancias_pedidas"] = r["ganancias"]
        r["ganancias"] = [1.0, 1.0, 1.0]
    return r, cand, excl


def depuracion(post, cand, excl):
    d = post * 0.35
    d[excl["saturado"]] = d[excl["saturado"]] * 0.5 + np.array([0.0, 0.0, 0.5])      # azul: muy saturado
    d[excl["fuente"] | excl["recortado"]] = np.array([0.6, 0.0, 0.0])                # rojo: fuente de luz / recortado
    cand_d = cv2.dilate(cand.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    d[cand_d] = np.array([0.0, 1.0, 0.2])                                            # verde: usados como blanco
    return d


def a8(x):
    rng = np.random.default_rng(0)
    x = np.clip(x, 0, 1) * 255
    x = x + (rng.random(x.shape[:2] + (1,)) + rng.random(x.shape[:2] + (1,)) - 1)   # dithering triangular
    return np.clip(np.round(x), 0, 255).astype(np.uint8)


def guardar(path, img):
    cv2.imwrite(path, a8(img)[..., ::-1])


def procesar_toma(video, cfg, lut, salida):
    n = cfg["normalizacion"]
    info = sondear(video)
    dur = float(info["duration"])
    ts = [dur * (i + 0.5) / n["frames_por_toma"] for i in range(n["frames_por_toma"])]
    res = []
    for t in ts:
        src, rango = decodificar_frame(video, t, cfg["entrada"]["rango"], cfg["entrada"]["matriz"], info)
        h, w = src.shape[:2]
        sw = n["ancho_trabajo"]
        pequeno = cv2.resize(src, (sw, int(h * sw / w)), interpolation=cv2.INTER_AREA)
        post_p = aplicar_lut(pequeno, lut)
        r, cand, excl = estimar(post_p, pequeno, cfg)
        r["t"] = t
        res.append((r, src, post_p, cand, excl))
    r, src, post_p, cand, excl = res[len(res) // 2]
    if len(res) > 1:                                           # un solo juego de ganancias por toma
        r["ganancias"] = np.median([x[0]["ganancias"] for x in res], axis=0).tolist()
    g = np.array(r["ganancias"])
    post = aplicar_lut(src, lut)
    if n["espacio"] == "linear" and r["corregir"]:
        norm = aplicar_lut(lin_a_slog3(slog3_a_lin(src) * g).clip(0, 1).astype(np.float32), lut)
    else:
        norm = post * g
    os.makedirs(salida, exist_ok=True)
    nombre = os.path.splitext(os.path.basename(video))[0]
    guardar(os.path.join(salida, "1_etapa1.png"), post)
    guardar(os.path.join(salida, "2_normalizado.png"), norm)
    dbg = depuracion(post_p, cand, excl)
    dbg_full = cv2.resize(dbg, (post.shape[1], post.shape[0]), interpolation=cv2.INTER_NEAREST)
    guardar(os.path.join(salida, "3_depuracion.png"), dbg_full)
    rep = dict(toma=nombre, archivo=video,
               ffprobe={k: info.get(k) for k in ("width", "height", "pix_fmt", "color_range", "color_space", "color_transfer")},
               rango_usado=rango, matriz=cfg["entrada"]["matriz"], espacio=n["espacio"], fuerza=n["fuerza"],
               t_frame=r.pop("t"), **r)
    if r.get("blanco_estimado"):
        w2 = np.median((post_p * g)[cand], axis=0)
        rep["blanco_tras_correccion"] = w2.tolist()
        rep["r_menos_b_tras_correccion"] = float(w2[0] - w2[2])
    json.dump(rep, open(os.path.join(salida, "report.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return rep, post, norm, dbg_full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--config")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "etapa2"))
    a = ap.parse_args()
    cfg = cargar_config(a.config)
    lut = load_cube(buscar_lut("Sony S-Log3 to Rec.709"))
    filas = []
    for v in a.videos:
        nombre = os.path.splitext(os.path.basename(v))[0]
        rep, post, norm, dbg = procesar_toma(v, cfg, lut, os.path.join(a.out, nombre))
        print(nombre, "corregir" if rep["corregir"] else "REVISAR " + ",".join(rep["banderas"]),
              "| gan", np.round(rep["ganancias"], 3), "| n", rep["n_candidatos"], "| conf", round(rep["confianza"], 2),
              "| R-B antes/después", round(rep.get("r_menos_b_blanco", float("nan")), 3),
              round(rep.get("r_menos_b_tras_correccion", float("nan")), 3))
        h = 360
        w = int(post.shape[1] * h / post.shape[0])
        f = lambda im, m=cv2.INTER_AREA: cv2.resize(im, (w, h), interpolation=m)
        filas.append(np.hstack([f(post), f(norm), f(dbg, cv2.INTER_NEAREST)]))
    ancho = max(x.shape[1] for x in filas)
    filas = [np.pad(x, ((0, 0), (0, ancho - x.shape[1]), (0, 0))) for x in filas]
    guardar(os.path.join(a.out, "contact_sheet.png"), np.vstack(filas))


if __name__ == "__main__":
    main()
