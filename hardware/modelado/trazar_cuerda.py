"""
Sigue cada cuerda del collar del pecho como un tubo, desde el dije hacia arriba.

En cada paso toma las caras cercanas cuya normal es perpendicular a la cuerda; cada una propone
un punto del eje (centro − normal × radio). El eje sigue la mediana de las propuestas que caen
cerca. Se detiene cuando las propuestas se dispersan (llegó a un amarre o al collar del cuello).
Luego marca la superficie del tubo: caras a radio ≈ r del eje con normal radial.

Uso: python trazar_cuerda.py "forma preliminar.stl" salida_dir
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
m = trimesh.load_mesh(src, process=True)
cc = m.triangles_center; nn = np.nan_to_num(m.face_normals); ar = m.area_faces
T = cKDTree(cc)
INICIOS = {"izq": ([-9.8, -37.2, 200.0], [-0.45, 0.0, 1.0]), "der": ([15.5, -35.2, 200.0], [0.4, 0.0, 1.0])}
R, PASO = 1.25, 0.8
res = {}


def trazar(p, d, signo=1):
    p = np.array(p, float); d = np.array(d, float) * signo; d /= np.linalg.norm(d)
    eje = [p.copy()]; fallos = 0
    for k in range(400):
        q = p + d * PASO
        idx = np.array(T.query_ball_point(q, 2.6))
        if len(idx) == 0: break
        perp = np.abs(nn[idx] @ d) < 0.45
        prop = cc[idx][perp] - nn[idx][perp] * R
        cerca = np.linalg.norm(prop - q, axis=1) < 1.0 if len(prop) else np.zeros(0, bool)
        if cerca.sum() < 6:
            fallos += 1
            if fallos > 4: break
            p = q; eje.append(p.copy()); continue
        fallos = 0
        nuevo = np.median(prop[cerca], axis=0); dn = nuevo - p
        if np.linalg.norm(dn) > 0.2:
            dn /= np.linalg.norm(dn); d = 0.7 * d + 0.3 * dn; d /= np.linalg.norm(d)
        else:
            nuevo = q
        p = nuevo; eje.append(p.copy())
    return np.array(eje[:-4]) if fallos else np.array(eje)


for nom, (p, d) in INICIOS.items():
    res[nom] = trazar(p, d)
# segundas cuerdas: propuestas de eje densas a 2-3,5 mm del eje ya trazado
for nom in list(res):
    eje = res[nom]; TE_ = cKDTree(eje); hechas = 0
    for k in range(5, len(eje) - 5, 6):
        q = eje[k]; d = eje[min(k + 3, len(eje) - 1)] - eje[max(k - 3, 0)]; d /= np.linalg.norm(d)
        idx = np.array(T.query_ball_point(q, 4.5))
        perp = np.abs(nn[idx] @ d) < 0.45
        prop = cc[idx][perp] - nn[idx][perp] * R
        dd, _ = TE_.query(prop)
        cand = prop[(dd > 1.9) & (dd < 3.6)]
        if len(cand) < 10: continue
        cen = np.median(cand, axis=0)
        if (np.linalg.norm(cand - cen, axis=1) < 0.8).sum() < 8: continue
        if any(np.min(np.linalg.norm(v - cen, axis=1)) < 1.5 for kk, v in res.items() if kk != nom): continue
        a1, a2 = trazar(cen, d, 1), trazar(cen, d, -1)
        nuevo = np.vstack([a2[::-1], a1])
        if len(nuevo) > 15:
            res[f"{nom}_2"] = nuevo; hechas += 1; break
for k, v in res.items():
    print(k, "pasos", len(v), "z", round(v[:, 2].min(), 1), "→", round(v[:, 2].max(), 1), "largo", round(float(np.linalg.norm(np.diff(v, axis=0), axis=1).sum()), 1))
np.savez(out / "ejes.npz", **res)
# superficie del tubo
todos = np.vstack(list(res.values()))
TE = cKDTree(todos)
dist, j = TE.query(cc, workers=-1)
rad = cc - todos[j]
radn = rad / np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9)
tubo = (np.abs(dist - R) < 0.6) & ((nn * radn).sum(1) > 0.6)
m.submesh([np.nonzero(tubo)[0]], append=True).export(out / "a_cuerdas.stl")
cerca = np.nonzero(dist < 15)[0]
m.submesh([np.setdiff1d(cerca, np.nonzero(tubo)[0])], append=True).export(out / "b_resto.stl")
print("caras de cuerda", tubo.sum())
