"""
Paso 1 del collar: eje preciso de cada cuerda (ajuste de círculo en cortes perpendiculares cada 0,5 mm)
y perfil del radio a lo largo, para ubicar amarres y nudos (donde el material rodea la cuerda a r > 1,5).
Uso: python collar_ejes.py "forma preliminar.stl" ejes.npz salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh
from scipy.ndimage import gaussian_filter1d
src, ej_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
m = trimesh.load_mesh(src, process=True); E = np.load(ej_f)
R0 = 1.22

def remuestrear(p, paso=0.5):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    t = np.arange(0, s[-1], paso); return np.column_stack([np.interp(t, s, p[:, k]) for k in range(3)])

def ajuste(pts, c, r=R0):
    for _ in range(8):
        d = np.linalg.norm(pts - c, axis=1); sel = np.abs(d - r) < 0.3
        if sel.sum() < 8: return c, 0
        q = pts[sel]; dq = np.linalg.norm(q - c, axis=1)
        c = c + np.mean((q - c) * ((dq - r) / dq)[:, None], axis=0) * 1.5
    d = np.linalg.norm(pts - c, axis=1)
    ang = np.arctan2(*(pts[np.abs(d - r) < 0.15] - c).T[::-1]); cob = len(np.unique(np.floor((ang + np.pi) / (np.pi / 18)))) / 36
    return c, cob

res = {}
for k in ("izq", "der"):
    ej = remuestrear(gaussian_filter1d(E[k], 2, axis=0, mode="nearest"))
    nuevo, cob, ext = [], [], []
    for i, p in enumerate(ej):
        d = ej[min(i + 3, len(ej) - 1)] - ej[max(i - 3, 0)]; d /= np.linalg.norm(d)
        u = np.cross(d, [0, 1, 0]); u /= np.linalg.norm(u); w = np.cross(d, u)
        s = m.section(plane_normal=d, plane_origin=p)
        if s is None: nuevo.append(p); cob.append(0); ext.append(0); continue
        P = np.vstack(s.discrete); P = P[np.linalg.norm(P - p, axis=1) < 3.5]
        q2 = np.c_[(P - p) @ u, (P - p) @ w]
        c2, cb = ajuste(q2, np.zeros(2))
        nuevo.append(p + u * c2[0] + w * c2[1]); cob.append(cb)
        dd = np.linalg.norm(q2 - c2, axis=1); a = np.arctan2(*(q2 - c2).T[::-1])
        anillo = (dd > 1.55) & (dd < 2.4)   # material alrededor (amarre)
        ext.append(len(np.unique(np.floor((a[anillo] + np.pi) / (np.pi / 18)))) / 36)
    nuevo = gaussian_filter1d(np.array(nuevo), 1.5, axis=0, mode="nearest")
    res[k] = nuevo; res[k + "_cob"] = np.array(cob); res[k + "_anillo"] = np.array(ext)
    print(k, "estaciones", len(nuevo), "z", nuevo[0, 2].round(1), "→", nuevo[-1, 2].round(1), "desplaz. medio", np.round(np.mean(np.linalg.norm(nuevo - ej, axis=1)), 2))
    za = nuevo[:, 2]; an = np.array(ext)
    print("  z con material alrededor (amarres):", [round(float(z), 1) for z, a in zip(za, an) if a > 0.7][::2])
np.savez(out / "ejes_fino.npz", **res)
