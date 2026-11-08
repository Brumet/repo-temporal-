"""
Costura exacta cabeza/cuerpo sobre la superficie: corte mínimo en el grafo de caras.

- Cuerpo (fijo): la cara plana de la correa (segmentar_correa.py) y todo lo que esté > 6 mm
  por debajo del canto aproximado.
- Cabeza (fija): todo lo que esté > 7 mm por encima.
- Cortar entre dos caras vecinas cuesta poco si la arista es un pliegue hundido (donde la correa
  se junta con las plumas) y mucho si la superficie es lisa. El corte mínimo encuentra el
  contorno cerrado más barato: el canto real de la correa.
- Después se eliminan islas: cualquier trozo suelto de un lado se pasa al otro.

Uso: python costura.py "forma preliminar.stl" borde_collar.json correa.npz salida_dir
Salida: costura.npz (índices de caras de la zona y etiqueta cabeza) + a_/b_/c_ STL para ver.
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, maxflow
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

src, borde, correa_f, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
SIG = 18.0    # grados: escala del pliegue
ITER_SUAVE = 6   # pasadas de alisado de la costura
LAMBDA = 0.08    # preferencia por cabeza (por mm² de cara) en la franja del canto
B = json.load(open(borde)); n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
m = trimesh.load_mesh(src, process=True)
Z = np.load(correa_f); zona, correa = Z["zona"], Z["correa"]
cu = m.submesh([zona], append=True)
d = cu.triangles_center - C0
hr = d @ n - np.interp(np.arctan2(d @ ey, d @ ex) % (2 * np.pi), TH, HB, period=2 * np.pi)
F = len(cu.faces)
adj = cu.face_adjacency
ang = np.degrees(cu.face_adjacency_angles)
convexo = cu.face_adjacency_convex
largo = np.linalg.norm(cu.vertices[cu.face_adjacency_edges[:, 0]] - cu.vertices[cu.face_adjacency_edges[:, 1]], axis=1)
# costo: pliegue hundido -> barato; liso -> caro; arista viva (cresta de pluma) -> intermedio
w = np.where(convexo, 0.35 + 0.65 * np.exp(-(ang / SIG) ** 2), np.exp(-(ang / SIG) ** 2))
w = largo * (w + 0.002)
g = maxflow.Graph[float](); nodos = g.add_nodes(F)
for (a, b), c in zip(adj, w):
    g.add_edge(int(a), int(b), float(c), float(c))
INF = 1e6
fuente = correa | (hr < -6.0)          # cuerpo
sumidero = (hr > 7.0) & ~correa       # cabeza
for i in np.nonzero(fuente)[0]:
    g.add_tedge(int(i), INF, 0)
for i in np.nonzero(sumidero)[0]:
    g.add_tedge(int(i), 0, INF)
# Preferencia leve: las caras que no son correa y están cerca o encima del canto prefieren cabeza
# (así una pluma bajo un amarre no se queda en el cuerpo). Los pliegues siguen mandando.
area = cu.area_faces
pref = (~correa) & (hr > -2.5) & ~fuente & ~sumidero
for i in np.nonzero(pref)[0]:
    g.add_tedge(int(i), 0, float(LAMBDA * area[i]))
flujo = g.maxflow()
cabeza = np.array([g.get_segment(int(i)) for i in range(F)], bool)   # 1 = lado sumidero = cabeza
print(f"corte: costo {flujo:.1f} · caras cabeza {cabeza.sum()} / {F}", flush=True)
# Quitar islas: en cada lado, solo se queda el componente conectado más grande
for lado in (True, False):
    sel = cabeza == lado
    ok = sel[adj[:, 0]] & sel[adj[:, 1]]
    gg = coo_matrix((np.ones(ok.sum()), (adj[ok, 0], adj[ok, 1])), shape=(F, F))
    nc, lab = connected_components(gg, directed=False)
    tam = np.bincount(lab[sel], minlength=nc)
    grande = np.argmax(tam)
    islas = sel & (lab != grande)
    # las islas que tocan el borde de la zona (recorte) no son islas reales
    print(f"lado {'cabeza' if lado else 'cuerpo'}: {nc} grupos, islas reasignadas {islas.sum()} caras", flush=True)
    cabeza[islas & (np.abs(hr) < 12)] = not lado
# Alisar la costura: promedio de la etiqueta entre caras vecinas (no cruza la correa: queda en cuerpo)
val = cabeza.astype(float)
A = coo_matrix((np.ones(2 * len(adj)), (np.r_[adj[:, 0], adj[:, 1]], np.r_[adj[:, 1], adj[:, 0]])), shape=(F, F)).tocsr()
deg = np.asarray(A.sum(1)).ravel() + 1
for _ in range(ITER_SUAVE):
    val = (A @ val + val) / deg
    val[fuente] = 0.0; val[sumidero] = 1.0
cabeza = val > 0.5
np.savez(out / "costura.npz", zona=zona, cabeza=cabeza)
cu.submesh([np.nonzero(cabeza)[0]], append=True).export(out / "c_cabeza.stl")
cu.submesh([np.nonzero(~cabeza)[0]], append=True).export(out / "b_cuerpo.stl")
