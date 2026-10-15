"""Etapa 4: look. 4a enfriamiento, 4b LUT creativo con intensidad, 4c HSL secundario inverso, 4d viñeta."""
import numpy as np, cv2

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def enfriar(img, t):
    out = np.array(img, np.float32, copy=True)
    out[..., 0] *= 1 - t
    out[..., 2] *= 1 + t
    return out


def creativo(img, lut, alpha):
    """salida = entrada + alpha * (LUT(entrada) - entrada)"""
    from etapa1 import aplicar_lut
    x = np.clip(img, 0, 1)
    return x + alpha * (aplicar_lut(x, lut).astype(np.float32) - x)


def _sstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def hsl_inverso(img, c):
    """Protege rojos/naranjas (piel) y aplica temperatura/tinte/saturación al resto, con máscara suave."""
    x = np.clip(img, 0, 1).astype(np.float32)
    hsv = cv2.cvtColor(x, cv2.COLOR_RGB2HSV)
    h, s = hsv[..., 0], hsv[..., 1]
    lo, hh = c["proteger_matiz_grados"]
    centro, medio = (lo + hh) / 2, (hh - lo) / 2
    hc = ((h - centro + 180) % 360) - 180
    prot = (1 - _sstep((np.abs(hc) - medio) / max(c["feather_grados"], 1e-3))) * _sstep((s - c["sat_min"]) / 0.1)
    m = (1 - prot)[..., None]
    adj = x.copy()
    adj[..., 0] *= 1 - c["temperatura"]
    adj[..., 2] *= 1 + c["temperatura"]
    adj[..., 1] *= 1 + c["tinte"]
    Y = (adj @ LUMA)[..., None]
    adj = Y + c["saturacion"] * (adj - Y)
    return x * (1 - m) + adj * m


def mapa_vineta(w, h, v):
    """Exponente p(r) por píxel: salida = entrada ** p. r = distancia circular / semidiagonal."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt((xx - (w - 1) / 2) ** 2 + (yy - (h - 1) / 2) ** 2) / (np.hypot(w, h) / 2)
    return (1 + v["A"] * np.maximum(0, r - v["r0"]) ** v["k"]).astype(np.float32)


def vineta(img, p):
    return np.power(np.clip(img, 1e-6, 1), p[..., None])
