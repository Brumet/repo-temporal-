"""
Barbas como LÍNEAS CONTINUAS: campo de fase θ en la superficie con ∇θ ≈ (2π/LAM)·e1 (e1 = a través de las barbas),
resuelto por mínimos cuadrados en las aristas (gradiente conjugado). Surco = ((1+cos θ)/2)^P: líneas finas y continuas
que siguen la dirección de cada pluma (sin puntos ni manchas del ruido de Gabor).
Uso (prueba en parche): python barbas_fase.py cuervo_reparado.stl campo.npz salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import cg
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import subdividir  # noqa: E402

LAM, AMP, POT, ALFA_B = 0.42, 0.04, 3.0, np.radians(40)


def fase(V, F, e1, N):
    """θ por mínimos cuadrados: θj − θi ≈ ω (xj − xi)·d_ij, con d_ij = e1 promedio alineado (campo de líneas)."""
    t = trimesh.Trimesh(V, F, process=False); E = t.edges_unique; i, j = E[:, 0], E[:, 1]
    abajo = np.array([0, 0, -1.0]); dt = abajo - N * (N @ abajo)[:, None]
    s = np.sign((e1 * dt).sum(1)); s[s == 0] = 1; e = e1 * s[:, None]      # orientar hacia abajo (consistencia local)
    ej = e[j] * np.sign((e[i] * e[j]).sum(1))[:, None]
    d = e[i] + ej; d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    w = 2 * np.pi / LAM; b = w * ((V[j] - V[i]) * d).sum(1)
    n = len(V); m = len(E)
    A = coo_matrix((np.r_[-np.ones(m), np.ones(m)], (np.r_[np.arange(m), np.arange(m)], np.r_[i, j])), shape=(m, n)).tocsr()
    L = (A.T @ A) + diags(np.full(n, 1e-6)); rhs = A.T @ b
    th, info = cg(L, rhs, maxiter=3000, rtol=1e-6)
    return th


def direccion_geometrica(V, N, hL, T):
    """Barbas desde la forma de la pluma: bajan hacia la punta y salen del raquis (cresta) hacia el borde a ALFA_B."""
    abajo = np.array([0, 0, -1.0]); f = abajo - N * (N @ abajo)[:, None]; f /= np.maximum(np.linalg.norm(f, axis=1, keepdims=True), 1e-9)
    l = np.cross(N, f)
    _, J = T.query(V, k=30, workers=-1)
    D = V[J] - V[:, None, :]; u = (D * l[:, None]).sum(2); dh = hL[J] - hL[:, None]
    g = (u * dh).sum(1) / np.maximum((u * u).sum(1), 1e-9)        # pendiente lateral del relieve de la pluma
    lado = -np.sign(g); lado[lado == 0] = 1                          # cuesta abajo = hacia el borde
    b = np.cos(ALFA_B) * f + np.sin(ALFA_B) * lado[:, None] * l      # dirección de la barba
    return np.cross(N, b)                                            # e1: a través de las barbas


if __name__ == "__main__":
    ref_f, campo_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    ref = trimesh.load_mesh(ref_f, process=True); C = np.load(campo_f); TR = cKDTree(ref.vertices)
    PAR = {"espalda": ((-15, 15), (25, 60), (215, 245)), "ala": ((28, 55), (-25, 15), (185, 225))}
    for nom, (xr, yr, zr) in PAR.items():
        c = ref.triangles_center
        sel = (c[:, 0] > xr[0]) & (c[:, 0] < xr[1]) & (c[:, 1] > yr[0]) & (c[:, 1] < yr[1]) & (c[:, 2] > zr[0]) & (c[:, 2] < zr[1])
        p = ref.submesh([np.nonzero(sel)[0]], append=True); p.export(out / f"{nom}_0_original.stl")
        _, j0 = TR.query(p.vertices)
        V0 = p.vertices + 0.5 * np.clip(C["h"][j0], -0.2, 0.2)[:, None] * p.vertex_normals
        s = subdividir(trimesh.Trimesh(V0, p.faces, process=False), 2); V, N = s.vertices, s.vertex_normals
        _, j = TR.query(V, workers=-1)
        coh, en = C["coh"][j], C["en"][j]
        cuero = np.clip((en - 0.12) / 0.05, 0, 1) * np.clip((0.55 - coh) / 0.15, 0, 1)
        wgt = np.clip((coh - 0.42) / 0.25, 0, 1) * np.clip((en - 0.008) / 0.015, 0, 1) * np.clip(1 - (C["curv"][j] - 0.03) / 0.05, 0, 1) * (1 - cuero)
        # dirección: la de las barbas esculpidas donde las hay (ala); si no, la de la forma de la pluma (espalda)
        hL = np.load(Path(campo_f).parent / "hL.npy")
        cerca = np.unique(j); Tl = cKDTree(ref.vertices[cerca])
        eg = np.zeros((len(ref.vertices), 3)); eg[cerca] = direccion_geometrica(ref.vertices[cerca], ref.vertex_normals[cerca], hL[cerca], Tl)
        usa_esc = np.clip((en - 0.05) / 0.03, 0, 1) > 0.5
        e1 = np.where(usa_esc[:, None], C["e1"][j], eg[j])
        wgt = np.maximum(wgt, (~usa_esc) * np.clip((C["curv"][j] < 0.08) * 1.0, 0, 1) * (1 - cuero) * (np.abs(hL[j]) > -1))
        th = fase(V, s.faces, e1, N)
        surco = ((1 + np.cos(th)) / 2) ** POT
        d = -AMP * surco * wgt
        borde = np.zeros(len(p.vertices), bool); borde[np.unique(p.edges_sorted[trimesh.grouping.group_rows(p.edges_sorted, require_count=1)])] = True
        _, jp = cKDTree(p.vertices).query(V); d[borde[jp]] = 0
        trimesh.Trimesh(V + N * d[:, None], s.faces, process=False).export(out / f"{nom}_6_fase.stl")
        print(nom, "vértices", len(V), "peso medio", round(float(wgt.mean()), 2), flush=True)
