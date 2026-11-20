"""
Pico natural (opción 1 de Bru): quita el aro de la nariz y las ranuras de las placas; conserva la banda de la base.

1. Región del pico: a lo largo del eje punta→base (t) hasta antes de las plumas.
2. Superficie lisa de referencia: suavizado Taubin (no encoge) dentro de la región, borde fijo.
3. Lo que sobresale de la lisa (H > UMB) se separa en piezas conectadas: la que cruza la parte de ARRIBA a la altura
   de la banda es la banda → se conserva; el resto (aros de la nariz, filos de placas) se aplana.
4. Resultado: posiciones nuevas para los vértices del modelo de referencia (pico_natural.npz) que luego usa
   superficie_final.py; ahí el pico no lleva barbas sino un grano fino de queratina.
Uso: python pico_natural.py cuervo_reparado.stl salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components

A = np.array([6.6, -89.1, 240.6]); B = np.array([3.0, -62.0, 272.0])        # punta → base del pico
T_FIN, T_FADE, R_MAX, UMB = 22.5, 2.5, 11.5, 0.30
ref_f, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
m = trimesh.load_mesh(ref_f, process=True); V = m.vertices.copy(); N = m.vertex_normals; n = len(V)
u = (B - A) / np.linalg.norm(B - A); t = (V - A) @ u; r = np.linalg.norm(V - A - np.outer(t, u), axis=1)
reg = (t > -3) & (t < T_FIN) & (r < R_MAX)
idx = np.nonzero(reg)[0]; print("vértices del pico", len(idx))
E = m.edges_unique; A_ = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
W = diags(1 / np.maximum(np.asarray(A_.sum(1)).ravel(), 1)) @ A_
S = V.copy(); libre = reg.copy()
for _ in range(700):                                      # Taubin: λ / μ alternado, solo dentro de la región
    for f in (0.5, -0.505):
        S2 = S + f * ((W @ S) - S); S[libre] = S2[libre]
H = ((V - S) * N).sum(1)
sale = reg & (H > UMB)
sub = A_[sale][:, sale]; nc, lab = connected_components(sub, directed=False)
iv = np.nonzero(sale)[0]
banda = np.zeros(n, bool)
arriba = np.array([0, 0, 1.0]) - u * u[2]; arriba /= np.linalg.norm(arriba)
for k in range(nc):
    g = iv[lab == k]
    if len(g) < 30: continue
    tt = t[g]; lado = np.abs(((V[g] - A - np.outer(t[g], u)) @ np.cross(u, arriba)))
    alto = (V[g] - A - np.outer(t[g], u)) @ arriba
    es_banda = (np.median(tt) > 14) and (alto.max() > 5.0) and (np.percentile(lado, 10) < 2.0)
    print(f"pieza {k}: {len(g)} vért, t {tt.min():.1f}-{tt.max():.1f}, lado mín {lado.min():.1f}, alto máx {alto.max():.1f} -> {'BANDA' if es_banda else 'se aplana'}")
    if es_banda: banda[g] = True
# dilatar la banda un poco (sus flancos) y mezclar
for _ in range(4): banda = banda | ((A_ @ banda.astype(float)) > 0) & reg
w = np.clip((T_FIN - t) / T_FADE, 0, 1) * np.clip((R_MAX - r) / 1.5, 0, 1) * reg
wb = banda.astype(float)
for _ in range(3): wb = 0.5 * wb + 0.5 * (W @ wb)
w = w * (1 - np.clip(wb * 1.6, 0, 1))
Vn = V + (S - V) * w[:, None]
np.savez(out / "pico_natural.npz", idx=np.nonzero(w > 1e-4)[0], pos=Vn[w > 1e-4], peso=w[w > 1e-4])
c = m.triangles_center; tc = (c - A) @ u; rc = np.linalg.norm(c - A - np.outer(tc, u), axis=1)
sel = np.nonzero((tc > -3) & (tc < 30) & (rc < 16))[0]
m.submesh([sel], append=True).export(out / "pico_antes.stl")
trimesh.Trimesh(Vn, m.faces, process=False).submesh([sel], append=True).export(out / "pico_despues.stl")
print("listo: vértices movidos", int((w > 1e-4).sum()), "desplazamiento máx mm", round(float(np.linalg.norm(Vn - V, axis=1).max()), 2))
