"""
Ubica cada globo ocular por su forma: desde un punto sobre el ojo crece por la superficie y se
detiene en el pliegue del párpado (arista cóncava fuerte). Guarda las caras del globo, su centro,
su eje (normal media) y su contorno.

Uso: python globo_ocular.py "forma preliminar.stl" salida_dir [umbral_grados]
"""
import sys, json
from pathlib import Path
from collections import deque
import numpy as np, trimesh

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
UMB = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
m = trimesh.load_mesh(src, process=True)
# centro aproximado de cada globo en el marco de la vista a lo largo del eje (x derecha, y arriba, mm)
VISTA = {"izq": ((-11.83, -64.28, 267.79), (-0.8261, -0.3428, -0.4472), (1.4, 0.3)),
         "der": ((17.48, -64.42, 268.01), (0.9142, -0.2308, -0.3332), (0.7, 2.3))}
RMAX = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
semillas = {}
for k, (c, e, (xr, yu)) in VISTA.items():
    c, e = np.array(c), np.array(e) / np.linalg.norm(e); f = -e
    VJ = json.load(open(str(out.parent.parent / "ojos2" / "ejes_vista.json")))[k]
    r, u = np.array(VJ["derecha"]), np.array(VJ["arriba"])
    semillas[k] = (list(c + r * xr + u * yu + e * 30), list(f))
res = {}
for nom, (o, d) in semillas.items():
    loc, _, tri = m.ray.intersects_location([o], [d], multiple_hits=False)
    p0, f0 = loc[0], tri[0]
    cerca = np.nonzero(np.linalg.norm(m.triangles_center - p0, axis=1) < RMAX)[0]
    sub = m.submesh([cerca], append=True)
    s0 = int(np.argmin(np.linalg.norm(sub.triangles_center - p0, axis=1)))
    adj = sub.face_adjacency; ang = np.degrees(sub.face_adjacency_angles); conv = sub.face_adjacency_convex
    pasa = conv | (ang < UMB)
    vec = [[] for _ in range(len(sub.faces))]
    for (a, b), ok in zip(adj, pasa):
        if ok: vec[a].append(b); vec[b].append(a)
    sel = np.zeros(len(sub.faces), bool); sel[s0] = True; q = deque([s0])
    while q:
        i = q.popleft()
        for j in vec[i]:
            if not sel[j]: sel[j] = True; q.append(j)
    g = sub.submesh([np.nonzero(sel)[0]], append=True)
    ar = g.area_faces; c = (g.triangles_center * ar[:, None]).sum(0) / ar.sum()
    z = (g.face_normals * ar[:, None]).sum(0); z /= np.linalg.norm(z)
    P = g.vertices - c; P2 = P - np.outer(P @ z, z)
    ev, V = np.linalg.eigh(P2.T @ P2 / len(P2))
    ancho = 2 * np.sqrt(np.maximum(ev[1:], 0) * 3)   # aprox. ejes del contorno (distribución uniforme)
    g.export(out / f"globo_{nom}.stl")
    res[nom] = {"semilla": p0.round(2).tolist(), "centro": c.round(3).tolist(), "eje": z.round(4).tolist(),
                "area_mm2": round(float(ar.sum()), 1), "ejes_contorno_mm": ancho.round(2).tolist()}
    print(nom, res[nom])
(out / "globos.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
