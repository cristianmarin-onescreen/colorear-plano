"""Etapa 1: S-Log3 -> Rec.709 con el LUT fijo. Referencia en Python + ffmpeg de producción."""
import glob, json, subprocess, sys, tempfile, os
import numpy as np, cv2, yaml
sys.path.insert(0, os.path.dirname(__file__))
from lut import load_cube, apply_lut

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar_config(path=None):
    return yaml.safe_load(open(path or os.path.join(ROOT, "config", "estilo.yaml"), encoding="utf-8"))


def buscar_lut(titulo, carpeta=None):
    """Identifica el LUT por la cabecera TITLE, no por el nombre."""
    for p in glob.glob(os.path.join(carpeta or os.path.join(ROOT, "luts"), "*.cube")):
        for ln in open(p, encoding="utf-8", errors="ignore"):
            if ln.startswith("TITLE"):
                if titulo in ln:
                    return p
                break
    raise FileNotFoundError(f"LUT con TITLE '{titulo}' no encontrado")


def sondear(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,pix_fmt,r_frame_rate,color_range,color_space,color_transfer,duration",
                        "-of", "json", video], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)["streams"][0]


def decodificar_frame(video, t, rango="auto", matriz="bt709", info=None):
    """Frame -> RGB float32 0-1 en rango completo (sin LUT). Devuelve (img, rango_usado)."""
    info = info or sondear(video)
    if rango == "auto":
        pc = info.get("color_range") in ("pc", None, "unknown") or info["pix_fmt"].startswith("yuvj")
        rango = "full" if pc else "limited"
    rin = "pc" if rango == "full" else "tv"
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1",
                        "-vf", f"setparams=range={rin},scale=in_range={rin}:in_color_matrix={matriz}:out_range=pc,format=rgb48be", out],
                       check=True)
        im = cv2.imread(out, cv2.IMREAD_UNCHANGED)
    return im[..., ::-1].astype(np.float32) / 65535.0, rango


def aplicar_lut(img, lut, chunk=400_000):
    sh = img.shape
    flat = img.reshape(-1, 3)
    out = np.empty_like(flat)
    for i in range(0, len(flat), chunk):
        out[i:i + chunk] = apply_lut(flat[i:i + chunk].astype(np.float64), lut)
    return out.reshape(sh)


def lut_ffmpeg(png_in, lut_path, png_out):
    """Producción: lut3d tetraédrico de ffmpeg sobre un PNG de 16 bits (la ruta del LUT se pasa copiada a un nombre simple)."""
    d = os.path.dirname(os.path.abspath(png_out))
    import shutil
    tmp = os.path.join(d, "_lut.cube")
    shutil.copy(lut_path, tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", png_in, "-vf",
                    "format=gbrp16le,lut3d=file=_lut.cube:interp=tetrahedral,format=rgb48be", png_out],
                   check=True, cwd=d)
    os.remove(tmp)
