"""
Separa la zona del cuello en "piezas lisas" cortando por los pliegues hundidos y mide cada una.
Sirve para clasificar collar (banda, cuerdas, amarres) contra plumas.

Uso: python piezas_collar.py "forma preliminar.stl" borde_collar.json correa.npz salida_dir [hundido]
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

src, borde, correa_f, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
HUNDIDO = float(sys.argv[5]) if len(sys.argv) > 5 else 10.0
B = json.load(open(borde)); n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
m = trimesh.load_mesh(src, process=True)
Z = np.load(correa_f); zona, plana = Z["zona"], Z["correa"]
cu = m.submesh([zona], append=True); F = len(cu.faces); cc = cu.triangles_center
d = cc - C0; hr = d @ n - np.interp(np.arctan2(d @ ey, d @ ex) % (2 * np.pi), TH, HB, period=2 * np.pi)
adj = cu.face_adjacency; ang = np.degrees(cu.face_adjacency_angles); conv = cu.face_adjacency_convex
une = conv | (ang < HUNDIDO)
nc, lab = connected_components(coo_matrix((np.ones(une.sum()), (adj[une, 0], adj[une, 1])), shape=(F, F)), directed=False)
area = cu.area_faces
# por pieza: área, fracción de banda plana, ángulo convexo máximo (p95), altura media, distancia a la banda
p95 = np.zeros(nc); aconv = np.where(conv, ang, 0)
for k in range(nc):
    pass
ia = np.r_[adj[:, 0], adj[:, 1]]; va = np.r_[aconv, aconv]
orden = np.argsort(lab[ia]); ls = lab[ia][orden]; vs = va[orden]
cortes = np.searchsorted(ls, np.arange(nc + 1))
for k in range(nc):
    s = vs[cortes[k]:cortes[k + 1]]
    p95[k] = np.percentile(s, 97) if len(s) else 0
A = np.bincount(lab, area, nc)
fp = np.bincount(lab, area * plana, nc) / np.maximum(A, 1e-9)
hm = np.bincount(lab, area * hr, nc) / np.maximum(A, 1e-9)
dpl, _ = cKDTree(cc[plana]).query(cc, workers=-1)
dm = np.bincount(lab, area * dpl, nc) / np.maximum(A, 1e-9)
np.savez(out / "piezas.npz", zona=zona, lab=lab, area=A, plana=fp, p97=p95, hm=hm, dm=dm)
grandes = np.argsort(-A)[:60]
for k in grandes:
    print(f"pieza {k:6d} área {A[k]:8.1f} mm² · plana {fp[k]:.2f} · filo97 {p95[k]:5.1f}° · h {hm[k]:6.1f} · d_banda {dm[k]:5.1f}")
print("piezas:", nc)
