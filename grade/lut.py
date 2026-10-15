import numpy as np

def load_cube(path):
    n, rows = None, []
    for ln in open(path, encoding="utf-8", errors="ignore"):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("LUT_3D_SIZE"):
            n = int(s.split()[1])
        elif s[0] in "-0123456789.":
            rows.append([float(x) for x in s.split()])
    # el rojo varía más rápido -> array [b][g][r][3]
    return np.array(rows, np.float64).reshape(n, n, n, 3)

def apply_lut(rgb, lut):
    """Interpolación trilineal. rgb: (...,3) float en 0-1."""
    n = lut.shape[0]
    x = np.clip(rgb, 0, 1) * (n - 1)
    i0 = np.minimum(np.floor(x).astype(int), n - 2)
    f = x - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = 0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (fr if dr else 1 - fr) * (fg if dg else 1 - fg) * (fb if db else 1 - fb)
                out = out + w * lut[b0 + db, g0 + dg, r0 + dr]
    return out
