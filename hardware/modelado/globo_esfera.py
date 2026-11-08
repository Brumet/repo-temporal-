"""
Globo ocular por ajuste de esfera: desde el centro del ojo crece por la superficie mientras la
cara esté cerca de la esfera ajustada (de -DN mm por debajo —iris tallado, surco— a +DP mm por
encima). El párpado sobresale de la esfera y marca el borde. La esfera se re-ajusta en cada ronda.

Uso: python globo_esfera.py "forma preliminar.stl" salida_dir [DN] [DP]
"""
import sys, json
from pathlib import Path
from collections import deque
import numpy as np, trimesh

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
DN = float(sys.argv[3]) if len(sys.argv) > 3 else 1.2
DP = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
RMAX = 6.0
R0 = float(sys.argv[5]) if len(sys.argv) > 5 else 1.2
m = trimesh.load_mesh(src, process=True)
CENTROS = {"izq": [-12.14, -64.61, 268.97], "der": [17.62, -61.78, 268.02]}
EJES = {"izq": [-0.826, -0.247, -0.507], "der": [0.918, -0.172, -0.359]}


def esfera(P, w=None):
    w = np.ones(len(P)) if w is None else w
    A = np.c_[2 * P, np.ones(len(P))] * w[:, None]; b = (P ** 2).sum(1) * w
    x = np.linalg.lstsq(A, b, rcond=None)[0]; c = x[:3]; return c, np.sqrt(x[3] + c @ c)


res = {}
for nom, c0 in CENTROS.items():
    c0 = np.array(c0); e = np.array(EJES[nom]); e /= np.linalg.norm(e)
    loc, _, _ = m.ray.intersects_location([c0 + e * 20], [-e], multiple_hits=False)
    p0 = loc[0]
    cerca = np.nonzero(np.linalg.norm(m.triangles_center - p0, axis=1) < RMAX + 1)[0]
    sub = m.submesh([cerca], append=True); cc = sub.triangles_center; ar = sub.area_faces
    adj = sub.face_adjacency
    vec = [[] for _ in range(len(cc))]
    for a, b in adj: vec[a].append(b); vec[b].append(a)
    sel = np.linalg.norm(cc - p0, axis=1) < R0
    for ronda in range(8):
        cs, Rs = esfera(cc[sel], ar[sel])
        dev = np.linalg.norm(cc - cs, axis=1) - Rs
        ok = (dev > -DN) & (dev < DP) & (np.linalg.norm(cc - p0, axis=1) < RMAX)
        s0 = int(np.argmin(np.linalg.norm(cc - p0, axis=1)))
        nuevo = np.zeros(len(cc), bool); nuevo[s0] = True; q = deque([s0])
        while q:
            i = q.popleft()
            for j in vec[i]:
                if not nuevo[j] and ok[j]: nuevo[j] = True; q.append(j)
        if (nuevo == sel).all(): break
        sel = nuevo
    g = sub.submesh([np.nonzero(sel)[0]], append=True)
    g.export(out / f"globo_{nom}.stl")
    res[nom] = {"centro_esfera": cs.round(3).tolist(), "radio": round(float(Rs), 3), "area_mm2": round(float(ar[sel].sum()), 1),
                "eje": e.tolist(), "rondas": ronda + 1}
    print(nom, res[nom])
(out / "globos.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
