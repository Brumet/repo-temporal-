"""
Barbas de pluma orientadas por el detalle que ya trae la escultura.

1. Señal de barbas existente: h = banda de detalle (suavizado corto − largo) sobre la normal.
2. Dirección local: tensor de estructura del gradiente de h en el plano tangente (vecindad 0,5 mm, promediado 1,2 mm).
   El gradiente apunta a través de las barbas; la coherencia dice dónde hay barbas claras.
3. Síntesis: ruido de Gabor orientado (impulsos aleatorios con coseno a lo largo del gradiente) → surcos finos
   paralelos a las barbas existentes, cada LAM mm; solo donde la coherencia es alta.
4. Las barbas originales se conservan y se afinan un poco (realce suave de h).
Uso: python barbas.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import subdividir  # noqa: E402
from superficie_v3 import suavizar  # noqa: E402

LAM, AMP, KERN, REALCE = 0.45, 0.035, 0.9, 0.5


def campo_direccion(V, F, N):
    s1, s2 = suavizar(V, F, 1), suavizar(V, F, 12)
    h = ((s1 - s2) * N).sum(1)
    T = cKDTree(V)
    _, J = T.query(V, k=14, workers=-1)
    a = np.cross(N, np.where(np.abs(N[:, :1]) < 0.9, [[1, 0, 0]], [[0, 1, 0]])); a /= np.linalg.norm(a, axis=1, keepdims=True)
    b = np.cross(N, a)
    D = V[J] - V[:, None, :]; u = (D * a[:, None, :]).sum(2); v = (D * b[:, None, :]).sum(2); dh = h[J] - h[:, None]
    Suu, Suv, Svv = (u * u).sum(1), (u * v).sum(1), (v * v).sum(1); Suh, Svh = (u * dh).sum(1), (v * dh).sum(1)
    det = Suu * Svv - Suv ** 2 + 1e-12
    gu, gv = (Svv * Suh - Suv * Svh) / det, (Suu * Svh - Suv * Suh) / det
    g = gu[:, None] * a + gv[:, None] * b                                   # gradiente 3D tangente
    Jt = g[:, :, None] * g[:, None, :]                                      # tensor de estructura
    _, K = T.query(V, k=96, workers=-1)
    Jt = Jt[K].mean(1)
    w, e = np.linalg.eigh(Jt)                                              # ascendente
    e1 = e[:, :, 2]; e1 -= N * (e1 * N).sum(1)[:, None]; e1 /= np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-9)
    coh = (w[:, 2] - w[:, 1]) / (w[:, 2] + w[:, 1] + 1e-12)
    energia = np.sqrt(np.maximum(w[:, 2], 0))
    return h, e1, coh, energia


def gabor(Vs, e1s, rng, dens=22.0):
    """Ruido de Gabor orientado: dens impulsos por mm²."""
    T = cKDTree(Vs)
    area_aprox = len(Vs) * 0.09 ** 2 * 0.45
    n = int(area_aprox * dens); idx = rng.choice(len(Vs), size=min(n, len(Vs)), replace=False)
    P, D, W = Vs[idx], e1s[idx], rng.choice([-1.0, 1.0], size=len(idx)) * rng.uniform(0.6, 1.0, len(idx))
    fase = rng.uniform(0, 2 * np.pi, len(idx))
    G = np.zeros(len(Vs)); TP = cKDTree(P)
    vec = TP.query_ball_point(Vs, KERN * 1.6, workers=-1)
    for i, js in enumerate(vec):
        if not js: continue
        d = Vs[i] - P[js]; r2 = (d * d).sum(1)
        G[i] = (W[js] * np.exp(-np.pi * r2 / KERN ** 2) * np.cos(2 * np.pi * (d * D[js]).sum(1) / LAM + fase[js])).sum()
    return G / (np.std(G) + 1e-9)


if __name__ == "__main__":
    src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    m = trimesh.load_mesh(src, process=True)
    xr, yr, zr = (28, 55), (-25, 15), (185, 225)
    c = m.triangles_center
    sel = (c[:, 0] > xr[0]) & (c[:, 0] < xr[1]) & (c[:, 1] > yr[0]) & (c[:, 1] < yr[1]) & (c[:, 2] > zr[0]) & (c[:, 2] < zr[1])
    p = m.submesh([np.nonzero(sel)[0]], append=True)
    h, e1, coh, en = campo_direccion(p.vertices, p.faces, p.vertex_normals)
    print("coherencia p25/p50/p75", np.percentile(coh, [25, 50, 75]).round(2), "energía p50", np.percentile(en, 50).round(3))
    V0 = p.vertices + REALCE * np.clip(h, -0.2, 0.2)[:, None] * p.vertex_normals
    s = subdividir(trimesh.Trimesh(V0, p.faces, process=False), 2); Vs, Ns = s.vertices, s.vertex_normals
    _, j = cKDTree(p.vertices).query(Vs, workers=-1)
    # solo donde ya hay barbas (coherencia y energía) y lejos de los cantos de la pluma (curvatura alta)
    curv = np.abs(((p.vertices - suavizar(p.vertices, p.faces, 3)) * p.vertex_normals).sum(1))
    w = np.clip((coh[j] - 0.35) / 0.3, 0, 1) * np.clip((en[j] - 0.04) / 0.06, 0, 1) * np.clip(1 - (curv[j] - 0.03) / 0.05, 0, 1)
    G = gabor(Vs, e1[j], np.random.default_rng(5))
    d = -AMP * np.clip(G - 0.3, 0, 2.5) ** 1.3 * w        # solo surcos finos (no bultos)
    borde = np.zeros(len(p.vertices), bool); borde[np.unique(p.edges_sorted[trimesh.grouping.group_rows(p.edges_sorted, require_count=1)])] = True
    d[borde[j]] = 0
    trimesh.Trimesh(Vs + Ns * d[:, None], s.faces, process=False).export(out / "ala_5_barbas.stl")
    np.save(out / "ala_coh.npy", coh)
    print("listo", len(s.faces))
