"""
Superficie v3 (prueba en parches), según referencias de Bru:
- ROCA tipo basalto: grano fino + POROS (ruido celular/Worley, pocos y dispersos) + caras astilladas suaves
  (facetas planas por celda de Voronoi). Sin red de líneas.
- PLUMAS: (1) suavizado leve donde hay líneas (quita el ruido de los triángulos), (2) realce SUAVE de la banda
  de escala de las barbas (diferencia entre un suavizado corto y uno largo: no realza la escala del triángulo),
  (3) teselación Phong para tener polígonos donde se ve el detalle.
Uso: python superficie_v3.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix, diags
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import subdividir, ruido, fbm  # noqa: E402

_r = np.random.default_rng(11); _H = _r.integers(0, 2 ** 31, size=(3,))


def _hash(c):
    h = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return (h ^ (h >> 16)) & 0x7FFFFFFF


def worley(p, celda, semilla=0):
    """Distancia al punto-semilla más cercano (F1), id de su celda y vector al punto. Celdas de 'celda' mm."""
    q = p / celda; base = np.floor(q).astype(np.int64)
    mejor = np.full(len(p), 9e9); ide = np.zeros(len(p), np.int64); vec = np.zeros_like(p)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + [dx, dy, dz]; h = _hash(c + semilla * 977)
                off = np.c_[(h % 1000) / 1000, ((h // 1000) % 1000) / 1000, ((h // 1000000) % 1000) / 1000]
                d = (c + off - q); dist = np.linalg.norm(d, axis=1)
                m = dist < mejor; mejor[m] = dist[m]; ide[m] = h[m]; vec[m] = d[m]
    return mejor * celda, ide, vec * celda


def roca_d(V, N):
    """Desplazamiento de basalto: grano fino + poros medianos y finos (sin facetas planas, sin líneas)."""
    grano = 0.028 * fbm(V / 0.35, 3) + 0.04 * fbm(V / 1.8, 2)
    f1, ide, _ = worley(V, 1.3, 1); hay = (ide % 100) < 55                       # poros medianos (55 % de celdas)
    r = 0.16 + 0.14 * ((ide // 100) % 100) / 100
    poro = -0.20 * np.clip(1 - f1 / r, 0, 1) ** 1.5 * hay
    f1b, ideb, _ = worley(V, 0.55, 2); hayb = (ideb % 100) < 45                # poros finos
    poro_f = -0.08 * np.clip(1 - f1b / 0.13, 0, 1) * hayb
    return grano + poro + poro_f


def suavizar_escalar(d, F, it):
    nV = len(d); t = trimesh.Trimesh(np.zeros((nV, 3)), F, process=False); E = t.edges_unique
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nV, nV)).tocsr()
    W = diags(1 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A
    for _ in range(it): d = 0.5 * d + 0.5 * (W @ d)
    return d


def roca(V, N, F):
    return V + N * suavizar_escalar(roca_d(V, N), F, 2)[:, None]


def suavizar(V, F, it):
    nV = len(V); t = trimesh.Trimesh(V, F, process=False); E = t.edges_unique
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nV, nV)).tocsr()
    W = diags(1 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A
    S = V.copy()
    for _ in range(it): S = 0.5 * S + 0.5 * (W @ S)
    return S


def plumas(V, F, N, beta=0.15, alfa=0.7):
    s1, s2 = suavizar(V, F, 1), suavizar(V, F, 20)
    banda = ((s1 - s2) * N).sum(1)                       # detalle de la escala de las barbas (~0,5–2 mm)
    banda = np.clip(banda, -0.25, 0.25)
    return V + beta * (s1 - V) + alfa * banda[:, None] * N, banda


if __name__ == "__main__":
    src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    m = trimesh.load_mesh(src, process=True)
    P = {"roca": ((35, 92), (-75, 5), (2, 40)), "ala": ((28, 55), (-25, 15), (185, 225))}
    for nom, (xr, yr, zr) in P.items():
        c = m.triangles_center
        sel = (c[:, 0] > xr[0]) & (c[:, 0] < xr[1]) & (c[:, 1] > yr[0]) & (c[:, 1] < yr[1]) & (c[:, 2] > zr[0]) & (c[:, 2] < zr[1])
        p = m.submesh([np.nonzero(sel)[0]], append=True)
        if nom == "roca":
            s = subdividir(p, 3); r = trimesh.Trimesh(roca(s.vertices, s.vertex_normals, s.faces), s.faces, process=False)
        else:
            V2, banda = plumas(p.vertices, p.faces, p.vertex_normals)
            borde = np.zeros(len(V2), bool); borde[np.unique(p.edges_sorted[trimesh.grouping.group_rows(p.edges_sorted, require_count=1)])] = True
            V2[borde] = p.vertices[borde]
            r = subdividir(trimesh.Trimesh(V2, p.faces, process=False), 2)
            print("ala: banda p50/p95 mm", np.percentile(np.abs(banda), [50, 95]).round(3))
        r.export(out / f"{nom}_4_v3.stl"); p.export(out / f"{nom}_0_original.stl")
        print(nom, "listo", len(r.faces), flush=True)
