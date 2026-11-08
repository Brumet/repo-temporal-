"""
Costura por reconstrucción de la correa.

1. Desde la cara plana de la correa (segmentar_correa.py) crece hacia sus paredes laterales por aristas
   convexas o casi planas; se detiene en los pliegues hundidos (donde empieza el plumaje) y nunca a
   más de MAX_D mm de la cara plana.
2. Etiqueta: correa -> cuerpo. Resto: por encima de la correa más cercana -> cabeza; por debajo -> cuerpo.
3. Una sola región por lado (islas reasignadas) y alisado leve del borde.

Uso: python costura2.py "forma preliminar.stl" borde_collar.json correa.npz salida_dir
"""
import sys, json
from pathlib import Path
from collections import deque
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

MAX_D = 2.5        # mm desde la cara plana
K_APERTURA = 4    # filas de caras
HUNDIDO = 8.0      # grados: una arista cóncava más cerrada que esto es pliegue (frontera)
src, borde, correa_f, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
B = json.load(open(borde)); n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
m = trimesh.load_mesh(src, process=True)
Z = np.load(correa_f); zona, plana = Z["zona"], Z["correa"]
cu = m.submesh([zona], append=True)
F = len(cu.faces); cc = cu.triangles_center
d = cc - C0
hr = d @ n - np.interp(np.arctan2(d @ ey, d @ ex) % (2 * np.pi), TH, HB, period=2 * np.pi)
dplana, jp = cKDTree(cc[plana]).query(cc, workers=-1)

adj = cu.face_adjacency; ang = np.degrees(cu.face_adjacency_angles); conv = cu.face_adjacency_convex
pasa = conv | (ang < HUNDIDO)
vec = [[] for _ in range(F)]
for (a, b), ok in zip(adj, pasa):
    if ok:
        vec[a].append(b); vec[b].append(a)
correa = plana.copy()
cola = deque(np.nonzero(plana)[0])
while cola:
    i = cola.popleft()
    for j in vec[i]:
        if not correa[j] and dplana[j] < MAX_D:
            correa[j] = True; cola.append(j)
print(f"correa: cara plana {plana.sum()} + paredes {correa.sum() - plana.sum()} caras", flush=True)

_, jc = cKDTree(cc[correa]).query(cc, workers=-1)
encima = hr - hr[correa][jc]
cabeza = (~correa) & (encima > 0)
# islas: una sola región por lado
for lado in (True, False):
    sel = cabeza == lado
    ok = sel[adj[:, 0]] & sel[adj[:, 1]]
    nc, lab = connected_components(coo_matrix((np.ones(ok.sum()), (adj[ok, 0], adj[ok, 1])), shape=(F, F)), directed=False)
    tam = np.bincount(lab[sel], minlength=nc)
    islas = sel & (lab != np.argmax(tam)) & (np.abs(hr) < 12)
    if lado:
        islas &= ~correa
    cabeza[islas] = not lado
    print(f"{'cabeza' if lado else 'cuerpo'}: islas reasignadas {islas.sum()} caras", flush=True)
cabeza[correa] = False
# Apertura en el grafo de caras: quita parches unidos a la cabeza por hilos (sobre amarres y anillos)
A = coo_matrix((np.ones(2 * len(adj)), (np.r_[adj[:, 0], adj[:, 1]], np.r_[adj[:, 1], adj[:, 0]])), shape=(F, F)).tocsr()
er = cabeza.copy()
for _ in range(K_APERTURA):
    er = er & (A @ (~er).astype(float) == 0)
ok = er[adj[:, 0]] & er[adj[:, 1]]
nc, lab = connected_components(coo_matrix((np.ones(ok.sum()), (adj[ok, 0], adj[ok, 1])), shape=(F, F)), directed=False)
tam = np.bincount(lab[er], minlength=nc); nucleo = er & (lab == np.argmax(tam))
di = nucleo.copy()
for _ in range(K_APERTURA + 1):
    di = di | ((A @ di.astype(float) > 0) & cabeza)
quitado = cabeza & ~di & (np.abs(hr) < 12)
cabeza[quitado] = False
print(f"apertura: {quitado.sum()} caras de parches pasan al cuerpo", flush=True)
np.savez(out / "costura.npz", zona=zona, cabeza=cabeza)
cu.submesh([np.nonzero(cabeza)[0]], append=True).export(out / "c_cabeza.stl")
cu.submesh([np.nonzero(~cabeza)[0]], append=True).export(out / "b_cuerpo.stl")
print("caras cabeza", cabeza.sum(), "/", F)
