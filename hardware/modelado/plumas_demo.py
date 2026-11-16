"""
Barbas de pluma por pluma (prueba en parches).
1) Separa las plumas: componentes de la malla cortando en los pliegues cóncavos fuertes (donde una pluma monta sobre otra).
2) Por pluma: eje largo (PCA), sentido hacia la punta (las plumas apuntan hacia abajo/atrás), raquis = línea central.
3) Barbas en espiga: surcos inclinados TH grados hacia la punta, con el ángulo espejado a cada lado del raquis;
   raquis en leve relieve; se desvanecen en el borde de la pluma. Solo en piezas con forma de pluma.
Uso: python plumas_demo.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import subdividir, ruido  # noqa: E402  (reutiliza la teselación Phong y el ruido)

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
TH, LAM, PROF, PLIEGUE = np.radians(48), 0.32, 0.045, 22.0
G = np.array([0, 0.35, -1.0]); G /= np.linalg.norm(G)        # hacia donde apuntan las plumas
PARCHES = {"pecho": ((-12, 12), (-55, -25), (196, 226)), "ala": ((28, 55), (-25, 15), (185, 225))}
m = trimesh.load_mesh(src, process=True)


def plumas(p):
    F = len(p.faces); adj = p.face_adjacency
    ang = np.degrees(p.face_adjacency_angles); conc = ~p.face_adjacency_convex
    une = ~(conc & (ang > PLIEGUE))
    nc, lab = connected_components(coo_matrix((np.ones(une.sum()), (adj[une, 0], adj[une, 1])), shape=(F, F)), directed=False)
    return lab


for nom, (xr, yr, zr) in PARCHES.items():
    c = m.triangles_center
    sel = (c[:, 0] > xr[0]) & (c[:, 0] < xr[1]) & (c[:, 1] > yr[0]) & (c[:, 1] < yr[1]) & (c[:, 2] > zr[0]) & (c[:, 2] < zr[1])
    p = m.submesh([np.nonzero(sel)[0]], append=True); p.export(out / f"{nom}_0_original.stl")
    lab = plumas(p); ar = p.area_faces; cc = p.triangles_center; nf = p.face_normals
    s = subdividir(p, 2); V = s.vertices; N = s.vertex_normals
    _, jf = cKDTree(cc).query(V, workers=-1); lv = lab[jf]               # etiqueta de pluma por vértice
    d = np.zeros(len(V)); n_pl = 0
    for k in np.unique(lab):
        f = lab == k; A = ar[f].sum()
        if A < 5 or A > 450: continue
        X = cc[f]; w = ar[f] / A; mu = w @ X; C = ((X - mu) * w[:, None]).T @ (X - mu)
        ev, evec = np.linalg.eigh(C)
        nrm = (nf[f] * ar[f, None]).sum(0); nrm /= np.linalg.norm(nrm)
        a1 = evec[:, 2] - nrm * (evec[:, 2] @ nrm); a1 /= np.linalg.norm(a1)
        if np.sqrt(ev[2] / max(ev[1], 1e-9)) < 1.25: continue              # no es alargada: no es pluma
        if a1 @ G < 0: a1 = -a1                                            # hacia la punta
        a2 = np.cross(nrm, a1)
        iv = np.nonzero(lv == k)[0]; P = V[iv] - mu
        sa, ta = P @ a1, P @ a2
        # borde de la pluma: distancia a los vértices de otras plumas
        otros = np.nonzero((lv != k) & (np.linalg.norm(V - mu, axis=1) < np.sqrt(ev[2]) * 4 + 3))[0]
        db = cKDTree(V[otros]).query(V[iv])[0] if len(otros) else np.full(len(iv), 9.0)
        q = sa * np.sin(TH) - np.abs(ta) * np.cos(TH) + 0.08 * ruido(V[iv] / 1.2)
        surco = -PROF * (0.5 + 0.5 * np.cos(2 * np.pi * q / LAM)) ** 2
        raquis = 0.035 * np.exp(-(ta / 0.18) ** 2) - PROF * 0.5 * np.exp(-((np.abs(ta) - 0.32) / 0.08) ** 2)
        fade = np.clip((db - 0.15) / 0.45, 0, 1) * np.clip((np.abs(ta) - 0.12) / 0.2, 0, 1)
        d[iv] = surco * fade + raquis * np.clip((db - 0.15) / 0.45, 0, 1)
        n_pl += 1
    trimesh.Trimesh(V + N * d[:, None], s.faces, process=False).export(out / f"{nom}_2_textura.stl")
    s.export(out / f"{nom}_1_suave.stl")
    print(nom, "caras", len(p.faces), "plumas texturizadas", n_pl, "de", len(np.unique(lab)), flush=True)
