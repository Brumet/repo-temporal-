"""
Detecta las bandas de cuero del pecho (franja con cuenta = C, cinturón doble = D): piezas lisas (separadas por pliegues
hundidos) que son largas y HORIZONTALES (rodean el cuerpo), delgadas en altura. Las plumas apuntan hacia abajo.
Uso: python cuero_pecho.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
PLIEGUE = float(sys.argv[3]) if len(sys.argv) > 3 else 18.0
m = trimesh.load_mesh(src, process=True)
zona = np.nonzero((m.triangles_center[:, 2] > 185) & (m.triangles_center[:, 2] < 242) & (m.triangles_center[:, 1] < 15))[0]
p = m.submesh([zona], append=True); F = len(p.faces)
adj = p.face_adjacency; ang = np.degrees(p.face_adjacency_angles); conc = ~p.face_adjacency_convex
une = ~(conc & (ang > PLIEGUE))
nc, lab = connected_components(coo_matrix((np.ones(une.sum()), (adj[une, 0], adj[une, 1])), shape=(F, F)), directed=False)
cc, ar = p.triangles_center, p.area_faces
cuero = np.zeros(F, bool); filas = []
orden = np.argsort(lab); ls = lab[orden]; cortes = np.searchsorted(ls, np.arange(nc + 1))
for k in range(nc):
    f = orden[cortes[k]:cortes[k + 1]]; A = ar[f].sum()
    if A < 15: continue
    X = cc[f]; w = ar[f] / A; mu = w @ X; C = ((X - mu) * w[:, None]).T @ (X - mu)
    ev, evec = np.linalg.eigh(C); eje = evec[:, 2]
    largo = 4 * np.sqrt(ev[2]); alto_z = 4 * np.sqrt(max(w @ (X[:, 2] - mu[2]) ** 2, 0))
    horiz = abs(eje[2]) < 0.35
    es = horiz and largo > 14 and alto_z < 9 and largo / max(alto_z, 0.1) > 2.5
    if es: cuero[f] = True; filas.append((round(A), round(largo, 1), round(alto_z, 1), np.round(mu, 0).tolist()))
print("piezas", nc, "| bandas horizontales", len(filas))
for r in sorted(filas, reverse=True)[:20]: print(r)
np.savez(out / "cuero_pecho.npz", zona=zona, cuero=cuero)
p.submesh([np.nonzero(cuero)[0]], append=True).export(out / "a_cuero_pecho.stl")
