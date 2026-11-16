"""
Mejora de superficie v2 (prueba en parches):
- REALCE del detalle que ya trae la escultura (barbas de las plumas): h = (V − suavizado(V))·n ; V += ALFA·h·n.
  No inventa direcciones: profundiza lo que el escultor ya talló.
- Teselación Phong ×2 (quita facetas).
- Zonas lisas del cuerpo (cuero de correas y placas): grano de cuero (poros finos + arrugas suaves).
  Se decide por la energía de detalle fino local: mucho detalle = pluma (realce), poco = cuero (grano).
Uso: python superficie_demo.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import subdividir, ruido, fbm  # noqa: E402

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
ALFA, UMBRAL = 0.9, 0.035
PARCHES = {"ala": ((28, 55), (-25, 15), (185, 225)), "pecho": ((-12, 12), (-55, -25), (196, 226))}
m = trimesh.load_mesh(src, process=True)
for nom, (xr, yr, zr) in PARCHES.items():
    c = m.triangles_center
    sel = (c[:, 0] > xr[0] - 3) & (c[:, 0] < xr[1] + 3) & (c[:, 1] > yr[0] - 3) & (c[:, 1] < yr[1] + 3) & (c[:, 2] > zr[0] - 3) & (c[:, 2] < zr[1] + 3)
    p = m.submesh([np.nonzero(sel)[0]], append=True)
    V0, n0 = p.vertices.copy(), p.vertex_normals.copy()
    E = p.edges_unique; nV = len(V0)
    from scipy.sparse import coo_matrix, diags
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nV, nV)).tocsr()
    deg = np.asarray(A.sum(1)).ravel(); W = diags(1 / np.maximum(deg, 1)) @ A
    Vs = V0.copy()
    for _ in range(8): Vs = 0.5 * Vs + 0.5 * (W @ Vs)          # promedio de vecinos (paraguas)
    h = np.clip(((V0 - Vs) * n0).sum(1), -0.3, 0.3)
    borde = np.zeros(nV, bool); borde[np.unique(p.edges_sorted[trimesh.grouping.group_rows(p.edges_sorted, require_count=1)])] = True
    h[borde] = 0
    T = cKDTree(V0); vec = T.query_ball_point(V0, 1.2, workers=-1)
    energia = np.array([np.abs(h[i]).mean() for i in vec])
    pluma = energia > UMBRAL
    p2 = trimesh.Trimesh(V0 + (ALFA * h * pluma)[:, None] * n0, p.faces, process=False)
    s = subdividir(p2, 2); V, N = s.vertices, s.vertex_normals
    _, j = T.query(V, workers=-1); cuero = ~pluma[j]
    # transición suave entre zonas
    w = np.clip((UMBRAL - energia[j]) / 0.015 + 0.5, 0, 1)
    grano = 0.012 * fbm(V / 0.5, 3) - 0.035 * np.clip(ruido(V / 0.16 + 5) - 0.32, 0, None) - 0.02 * np.clip(np.abs(ruido(V / 2.2 + 9)) * -6 + 1, 0, 1) ** 3
    s2 = trimesh.Trimesh(V + N * (grano * w)[:, None], s.faces, process=False)
    # recorte final a la caja del parche
    cc = s2.triangles_center
    k = (cc[:, 0] > xr[0]) & (cc[:, 0] < xr[1]) & (cc[:, 1] > yr[0]) & (cc[:, 1] < yr[1]) & (cc[:, 2] > zr[0]) & (cc[:, 2] < zr[1])
    s2.submesh([np.nonzero(k)[0]], append=True).export(out / f"{nom}_3_realce.stl")
    print(nom, "vértices pluma %", round(100 * pluma.mean()), "energía p50/p90", np.percentile(energia, [50, 90]).round(3), flush=True)
