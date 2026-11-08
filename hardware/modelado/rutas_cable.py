"""
Ruta de los cables por dentro del cuervo hueco y largo a cortar.
Cavidad = interior del sólido a más de PARED mm de la superficie. Camino geodésico (más corto
por dentro) desde la bahía de la ESP32 en la roca hasta la cámara de cada porta-LED, y entre ojos.
Uso: python rutas_cable.py cuervo_reparado.stl ojos.json salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy import ndimage
from skimage.graph import MCP_Geometric
sol_f, oj_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
P, PARED, MARGEN = 0.75, 3.0, 0.1   # vóxel 0,75 mm; pared 3 mm (el cable puede ir pegado a la pared)
m = trimesh.load_mesh(sol_f, process=True)
v = m.voxelized(P).fill(); M = v.matrix; T = v.transform
print("vóxeles", M.shape, M.sum(), flush=True)
dist = ndimage.distance_transform_edt(M) * P
cav = dist > PARED + MARGEN
lab, n = ndimage.label(cav); grande = np.argmax(np.bincount(lab.ravel())[1:]) + 1; cav = lab == grande
idx2w = lambda ijk: trimesh.transform_points(np.asarray(ijk, float).reshape(-1, 3), T)
w2idx = lambda p: np.round(trimesh.transform_points(np.asarray(p, float).reshape(-1, 3), np.linalg.inv(T))).astype(int)
cav_ijk = np.argwhere(cav); cav_w = idx2w(cav_ijk)
def cercano(p):
    return tuple(cav_ijk[np.argmin(np.linalg.norm(cav_w - p, axis=1))])
J = json.load(open(oj_f)); ojos = {}
for nom in ("izq", "der"):
    F = J[nom]["marco"]; c, e = np.array(F["c"]), np.array(F["e"])
    ojos[nom] = c + e * (F["z_fondo"] - 1)      # salida de la cámara del porta-LED hacia el hueco
    print(nom, "salto a la cavidad mm", round(float(np.linalg.norm(idx2w([cercano(ojos[nom])])[0] - ojos[nom])), 1))
bahia = np.array([0.0, 25.0, 12.0])
coste = np.where(cav, 1.0, np.inf)
def ruta(a, b):
    mcp = MCP_Geometric(coste); mcp.find_costs([cercano(a)]); camino = np.array(mcp.traceback(cercano(b)))
    pw = np.vstack([a, idx2w(camino), b]); k = max(1, len(pw) // 60)
    lis = np.vstack([pw[::k], pw[-1]])
    return lis, float(np.linalg.norm(np.diff(pw, axis=0), axis=1).sum())
res = {}
for nom in ("der", "izq"):
    res[f"base_{nom}"] = ruta(bahia, ojos[nom])
res["der_izq"] = ruta(ojos["der"], ojos["izq"])
info = {}
for k, (pw, L) in res.items():
    pata = pw[(pw[:, 2] > 140) & (pw[:, 2] < 170)]
    info[k] = {"largo_mm": round(L), "pata_x": round(float(pata[:, 0].mean()), 1) if len(pata) else None}
    np.save(out / f"ruta_{k}.npy", pw)
print(json.dumps(info, indent=1)); json.dump(info, open(out / "rutas.json", "w"), indent=1)
