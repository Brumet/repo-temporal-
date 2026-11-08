"""
Clasifica las piezas lisas del cuello (piezas_collar.py) en collar o pluma por su ORIENTACIÓN:
la banda y las cuerdas se alargan alrededor del cuello (tangente al collar); las plumas apuntan
a lo largo del cuello. Amarres pequeños pegados a la banda también son collar.

Uso: python clasificar_collar.py "forma preliminar.stl" borde_collar.json piezas.npz salida_dir
Salida: collar.npz (máscara por cara de la zona) + a_collar.stl / b_resto.stl
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree

ELONG_MIN = 2.2      # largo/ancho mínimo para considerar "alargada"
ALIN_MIN = 0.75      # |cos| entre eje largo y la tangente del collar
LARGO_MIN = 5.0      # mm
REDONDEZ_MIN = 0.45  # sección redonda (cuerda) frente a lámina (pluma)
USAR_AMARRES = bool(int(sys.argv[5])) if len(sys.argv) > 5 else True
SOLO = sys.argv[6] if len(sys.argv) > 6 else ''
src, borde, piezas_f, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
B = json.load(open(borde)); n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
m = trimesh.load_mesh(src, process=True)
P = np.load(piezas_f); zona, lab = P["zona"], P["lab"]
cu = m.submesh([zona], append=True); cc = cu.triangles_center; ar = cu.area_faces
d = cc - C0; th = np.arctan2(d @ ey, d @ ex)
hr = d @ n - np.interp(th % (2 * np.pi), TH, HB, period=2 * np.pi)
nc = lab.max() + 1
orden = np.argsort(lab); ls = lab[orden]; cortes = np.searchsorted(ls, np.arange(nc + 1))
plana = P["plana"]
collar_p = np.zeros(nc, bool); info = {}; red_p = np.zeros(nc)
for k in range(nc):
    idx = orden[cortes[k]:cortes[k + 1]]
    A = ar[idx].sum()
    if A < 1.0:
        continue
    X = cc[idx]; w = ar[idx] / A; mu = (w[:, None] * X).sum(0)
    C = ((X - mu) * w[:, None]).T @ (X - mu)
    ev, V = np.linalg.eigh(C); ev = np.maximum(ev, 1e-9)
    eje = V[:, 2]; largo = 4 * np.sqrt(ev[2]); elong = np.sqrt(ev[2] / ev[1])
    tm = np.arctan2((mu - C0) @ ey, (mu - C0) @ ex)
    tang = -np.sin(tm) * ex + np.cos(tm) * ey
    alin = abs(eje @ tang)
    hmed = (w * hr[idx]).sum()
    tipo = "banda" if plana[k] > 0.3 else ""
    redondez = np.sqrt(ev[0] / ev[1])        # tubo ~0,5-1 · lámina plana ~0
    es = (plana[k] > 0.3) or (elong > ELONG_MIN and alin > ALIN_MIN and largo > LARGO_MIN and -9 < hmed < 4 and redondez > REDONDEZ_MIN)
    if SOLO == "banda": es = plana[k] > 0.3
    if SOLO == "alargada": es = es and plana[k] <= 0.3
    collar_p[k] = es
    info[k] = (A, largo, elong, alin, hmed, es)
    red_p[k] = redondez
collar = collar_p[lab]
# Amarres: piezas pequeñas (< 60 mm²) cuya mayor parte está a < 1,2 mm de piezas collar
dcol, _ = cKDTree(cc[collar]).query(cc, workers=-1)
cerca = np.bincount(lab, ar * (dcol < 0.8), nc) / np.maximum(np.bincount(lab, ar, nc), 1e-9)
peq = np.bincount(lab, ar, nc) < 60
am = (~collar_p) & peq & (cerca > 0.7) & (red_p > 0.3) & USAR_AMARRES
collar = (collar_p | am)[lab]
print(f"piezas collar: {collar_p.sum()} alargadas/banda + {am.sum()} amarres · caras {collar.sum()} / {len(lab)}")
np.savez(out / "collar.npz", zona=zona, collar=collar)
cu.submesh([np.nonzero(collar)[0]], append=True).export(out / "a_collar.stl")
cu.submesh([np.nonzero(~collar)[0]], append=True).export(out / "b_resto.stl")
