"""Etapa 3: luz adaptativa por toma. Curva monótona (PCHIP) por canal, anclada en los percentiles de la toma."""
import numpy as np
from scipy.interpolate import PchipInterpolator

LUMA = np.array([0.2126, 0.7152, 0.0722])
Q = np.array([0.5, 5, 25, 50, 75, 95, 99.5])


def percentiles(img, mask=None):
    Y = img @ LUMA
    if mask is not None:
        Y = Y[mask]
    return np.percentile(Y, Q)


def objetivos(p, cfg_luz):
    """Percentiles base de la toma -> percentiles objetivo (p0.5 y p99.5 anclados, medios con S suave)."""
    lo, hi = cfg_luz["ancla_negros"], cfg_luz["ancla_blancos"]
    rango = p[-1] - p[0]
    s = (hi - lo) / rango
    smax = cfg_luz["max_estiramiento"]
    if s > smax:                                  # no estirar más de lo que aguantan 8 bits
        hi = lo + smax * rango
    u = (p - p[0]) / rango
    k, c = cfg_luz["s_k"], cfg_luz["s_c"]
    y = lo + (hi - lo) * (u + k * u * (1 - u) * (u - c))
    f = cfg_luz["fuerza"]
    return p + f * (y - p)


def curva(p, cfg_luz, n=4096):
    """Tabla 1D (n puntos en 0-1). Hombro suave: p99.5 -> objetivo y 1.0 -> 1.0."""
    y = objetivos(p, cfg_luz)
    xs = np.concatenate([[0.0], p, [1.0]])
    ys = np.concatenate([[0.0], y, [1.0]])
    keep = np.concatenate([[True], np.diff(xs) > 1e-4])          # x estrictamente creciente
    xs, ys = xs[keep], ys[keep]
    ys = np.maximum.accumulate(ys + np.arange(len(ys)) * 1e-6)    # monótona
    t = np.linspace(0, 1, n)
    return np.clip(PchipInterpolator(xs, ys, extrapolate=True)(t), 0, 1.5)


def aplicar_curva(img, tabla):
    n = len(tabla)
    return np.interp(np.clip(img, 0, 1), np.linspace(0, 1, n), tabla)
