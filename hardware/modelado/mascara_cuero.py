"""
Máscara de cuero por vértice sobre cuervo_reparado.stl (lo que Bru marcó como cuero: A aro del cuello, B banda bajo el
pico, C franja del pecho, D cinturón doble, F cuerdas). A+B: máscara del collar ya clasificada (collar.npz).
C, D, F: contornos dibujados sobre la vista frontal (cámara ortográfica conocida) y proyectados con rayos: solo la
superficie VISIBLE dentro del contorno.
Uso: python mascara_cuero.py cuervo_reparado.stl "forma preliminar.stl" collar.npz salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
from matplotlib.path import Path as Poly

ref_f, orig_f, collar_f, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
ref = trimesh.load_mesh(ref_f, process=True); V = ref.vertices; TR = cKDTree(V)
# --- cámara frontal de cuero_candidatos.png (1000×1100 px, ortho 110 mm → 0,1 mm/px)
TGT = np.array([0, -30.0, 228.0]); v = np.array([0, -1, 0.12]); v /= np.linalg.norm(v)
X = np.cross([0, 0, 1.0], v); X /= np.linalg.norm(X); Y = np.cross(v, X); MMPX = 0.1


def a_mundo(px, py): return TGT + (px - 500) * MMPX * X + (550 - py) * MMPX * Y


C_POL = [(362, 568), (420, 575), (470, 588), (500, 592), (530, 588), (580, 577), (652, 568), (650, 586), (600, 606),
         (560, 625), (520, 638), (480, 638), (440, 623), (400, 606), (365, 586)]
D_POL = [(228, 738), (260, 742), (330, 762), (400, 770), (500, 768), (600, 768), (660, 760), (720, 730), (760, 705),
         (788, 694), (790, 728), (770, 775), (720, 820), (660, 850), (600, 870), (500, 874), (400, 868), (330, 852),
         (260, 830), (228, 805)]
CUERDAS = [[(190, 285), (240, 420), (300, 560), (400, 760), (458, 905)], [(790, 250), (762, 360), (735, 470), (650, 760), (602, 905)]]


def franja(pts, ancho=15):
    pts = np.array(pts, float); izq, der = [], []
    for i in range(len(pts)):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]; d /= np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
        izq.append(pts[i] + nrm * ancho); der.append(pts[i] - nrm * ancho)
    return np.vstack([izq, der[::-1]])


def proyectar(pol):
    P = Poly(np.array(pol, float)); x0, y0 = np.min(pol, 0); x1, y1 = np.max(pol, 0)
    gx, gy = np.meshgrid(np.arange(x0, x1, 1.0), np.arange(y0, y1, 1.0)); q = np.c_[gx.ravel(), gy.ravel()]
    q = q[P.contains_points(q)]
    o = np.array([a_mundo(px, py) for px, py in q]) + v * 300
    L, I, F = ref.ray.intersects_location(o, np.tile(-v, (len(o), 1)), multiple_hits=False)
    vs = np.unique(ref.faces[F].ravel()); return vs


m = np.zeros(len(V), bool)
for nom, pol in (("C", C_POL), ("D", D_POL), ("F_sup_izq", franja([(262, 545), (225, 420), (185, 280)], 13))):
    vs = proyectar(pol); m[vs] = True; print(nom, "vértices", len(vs))
# A + B: collar clasificado (caras de "forma preliminar")
orig = trimesh.load_mesh(orig_f, process=True); Cz = np.load(collar_f)
caras = Cz["zona"][Cz["collar"]] if "collar" in Cz.files else None
print("collar.npz:", Cz.files)
if caras is not None:
    pts = orig.vertices[np.unique(orig.faces[caras].ravel())]
    d, j = TR.query(pts, workers=-1); m[j[d < 0.3]] = True; print("A+B vértices", int((d < 0.3).sum()))
# F: cuerdas por sus ejes reales (tubo de 2,3 mm alrededor de cada hebra)
E = np.load(Path(collar_f).parent.parent / "cuerdas2" / "ejes.npz"); H = np.load(Path(collar_f).parent.parent / "collar3" / "hebras.npz")
ejes = np.vstack([E[k] for k in E.files] + [H[k] for k in ("izq", "der", "izq_eje", "der_eje")])
from scipy.spatial import cKDTree as _K
d, _ = _K(ejes).query(V, workers=-1); m |= d < 2.3; print("F vértices", int((d < 2.3).sum()))
# fuera el pico (no es cuero)
PA, PB = np.array([6.6, -89.1, 240.6]), np.array([3.0, -62.0, 272.0]); u = (PB - PA) / np.linalg.norm(PB - PA)
t = (V - PA) @ u; r = np.linalg.norm(V - PA - np.outer(t, u), axis=1); m &= ~((t > -9) & (t < 24) & (r < 13))
# cerrar huecos pequeños: dilatar 2 anillos y erosionar 1
A = ref.vertex_neighbors
for _ in range(2): m = m | np.array([m[nb].any() if len(nb) else False for nb in A])
m = m & np.array([m[nb].mean() > 0.4 if len(nb) else False for nb in A])
np.save(out / "cuero_vertices.npy", m)
print("cuero total", int(m.sum()), "de", len(V))
q = ref.copy(); col = np.tile([150, 150, 150, 255], (len(V), 1)); col[m] = [255, 120, 30, 255]; q.visual.vertex_colors = col.astype(np.uint8)
q.export(out / "mascara_cuero.ply")
