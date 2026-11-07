"""
Encuentra los triángulos de la CORREA del collar en la malla, para cortar exactamente por su borde.

La correa es una superficie lisa; las plumas tienen pliegues y aristas. Desde semillas puestas
sobre la correa (2 mm por debajo del canto aproximado de borde_collar.json) se hace crecer una
región a través de aristas cuyo ángulo diedro es menor que UMBRAL grados.

Uso: python segmentar_correa.py "forma preliminar.stl" borde_collar.json salida_dir [umbral]
Salida: correa.npz (índices de caras de la zona del cuello y máscara de la correa) + cuello.ply
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

src, borde, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
UMBRAL = float(sys.argv[4]) if len(sys.argv) > 4 else 30.0
B = json.load(open(borde))
n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
m = trimesh.load_mesh(src, process=True)


def h_rel(P):
    d = P - C0; th = np.arctan2(d @ ey, d @ ex) % (2 * np.pi)
    return d @ n - np.interp(th, TH, HB, period=2 * np.pi), th


hr, _ = h_rel(m.triangles_center)
zona = np.nonzero(np.abs(hr) < 14)[0]
cu = m.submesh([zona], append=True)
print("caras en la zona:", len(cu.faces), flush=True)
# Grafo de caras: unir vecinas si el diedro es suave
adj, ang = cu.face_adjacency, np.degrees(cu.face_adjacency_angles)
lisa = ang < UMBRAL
g = coo_matrix((np.ones(lisa.sum()), (adj[lisa, 0], adj[lisa, 1])), shape=(len(cu.faces),) * 2)
ncomp, lab = connected_components(g, directed=False)
# Semillas: punto de superficie 2 mm por debajo del canto, en 72 ángulos
hrc, thc = h_rel(cu.triangles_center)
semillas = set()
for t in np.linspace(0, 2 * np.pi, 72, endpoint=False):
    dth = np.abs((thc - t + np.pi) % (2 * np.pi) - np.pi)
    hb = np.interp(t, TH, HB, period=2 * np.pi)
    cand = np.nonzero((dth < 0.02) & (np.abs(hrc - (-2.0)) < 1.2))[0]
    if len(cand):
        r = (cu.triangles_center[cand] - C0) @ (np.cos(t) * ex + np.sin(t) * ey)
        semillas.add(lab[cand[np.argmax(r)]])           # la más externa (la correa sobresale)
tam = np.bincount(lab)
# descartar componentes gigantes que se hayan "escapado" por plumas lisas
print("tamaños semilla:", sorted([int(tam[c]) for c in semillas], reverse=True)[:12])
comps = [c for c in semillas if tam[c] < 0.35 * len(cu.faces)]
correa = np.isin(lab, comps)
print(f"umbral {UMBRAL}° · componentes semilla {len(semillas)} · usadas {len(comps)} · caras de correa {correa.sum()}")
np.savez(out / "correa.npz", zona=zona, correa=correa)
cu.submesh([np.nonzero(correa)[0]], append=True).export(out / "a_correa.stl")
cu.submesh([np.nonzero(~correa)[0]], append=True).export(out / "b_resto.stl")
