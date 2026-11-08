"""
Detecta las cuerdas del collar del pecho (tubos largos y delgados) en la parte alta del cuervo.

Separa la superficie en piezas lisas por los pliegues hundidos y marca como cuerda las piezas
tubulares: largas, de sección redonda y delgada. Une las que tocan el dije (colgante.stl).

Uso: python cuerdas.py "forma preliminar.stl" colgante.stl salida_dir [hundido]
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

src, colg_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
HUNDIDO = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0
m = trimesh.load_mesh(src, process=True)
zona = np.nonzero(m.triangles_center[:, 2] > 160)[0]
cu = m.submesh([zona], append=True); F = len(cu.faces); cc = cu.triangles_center; ar = cu.area_faces
adj = cu.face_adjacency; ang = np.degrees(cu.face_adjacency_angles); conv = cu.face_adjacency_convex
une = conv | (ang < HUNDIDO)
nc, lab = connected_components(coo_matrix((np.ones(une.sum()), (adj[une, 0], adj[une, 1])), shape=(F, F)), directed=False)
orden = np.argsort(lab); ls = lab[orden]; cortes = np.searchsorted(ls, np.arange(nc + 1))
tubo = np.zeros(nc, bool); filas = []
for k in range(nc):
    idx = orden[cortes[k]:cortes[k + 1]]; A = ar[idx].sum()
    if A < 3: continue
    X = cc[idx]; w = ar[idx] / A; mu = w @ X
    C = ((X - mu) * w[:, None]).T @ (X - mu); ev = np.maximum(np.linalg.eigvalsh(C), 1e-9)
    largo = 4 * np.sqrt(ev[2]); grueso = 4 * np.sqrt(ev[1]); red = np.sqrt(ev[0] / ev[1])
    es = largo > 7 and grueso < 4.2 and largo / grueso > 3.0 and red > 0.35
    tubo[k] = es
    if es: filas.append((round(A, 1), round(largo, 1), round(grueso, 2), round(red, 2), np.round(mu, 1).tolist()))
cuerda = tubo[lab]
print(f"piezas {nc} · tubos {tubo.sum()} · caras {cuerda.sum()}")
for f in sorted(filas, reverse=True)[:25]: print(f)
np.savez(out / "cuerdas.npz", zona=zona, cuerda=cuerda, lab=lab)
cu.submesh([np.nonzero(cuerda)[0]], append=True).export(out / "a_cuerdas.stl")
cu.submesh([np.nonzero(~cuerda)[0]], append=True).export(out / "b_resto.stl")
