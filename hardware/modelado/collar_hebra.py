"""
Eje de la hebra delgada (r ≈ 0,55) trenzada junto a cada cuerda: en cada corte perpendicular busca el círculo
pequeño pegado al círculo principal (RANSAC de radio fijo), luego da continuidad por ángulo y rellena huecos.
Uso: python collar_hebra.py "forma preliminar.stl" ejes_fino.npz salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh
from scipy.ndimage import median_filter, gaussian_filter1d
src, ej_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
m = trimesh.load_mesh(src, process=True); E = np.load(ej_f)
RH, RC = 0.55, 1.22
rng = np.random.default_rng(1)
def remuestrear(p, paso):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]; t = np.arange(0, s[-1] + 1e-9, paso)
    return np.column_stack([np.interp(t, s, p[:, k]) for k in range(3)])
def marcos(p):
    T = np.gradient(p, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = [np.cross(T[0], [0, 1, 0])]; U[0] /= np.linalg.norm(U[0])
    for i in range(1, len(p)):
        u = U[-1] - T[i] * (U[-1] @ T[i]); U.append(u / np.linalg.norm(u))
    U = np.array(U); return T, U, np.cross(T, U)
def ransac(q, a0=None, ven=0.6):
    r = np.linalg.norm(q, axis=1); c = q[(r > RC + 0.05) & (r < 2.5)]
    if a0 is not None:
        da = np.abs((np.arctan2(c[:, 1], c[:, 0]) - a0 + np.pi) % (2 * np.pi) - np.pi); c = c[da < ven + 0.4]
    if len(c) < 6: return None, 0
    best, bs = None, 0
    for _ in range(300):
        a, b = c[rng.integers(len(c), size=2)]; mid = (a + b) / 2; dv = b - a; L = np.linalg.norm(dv)
        if L < 0.15 or L > 2 * RH: continue
        h = np.sqrt(RH ** 2 - (L / 2) ** 2); nrm = np.array([-dv[1], dv[0]]) / L
        for cc in (mid + nrm * h, mid - nrm * h):
            dc = np.linalg.norm(cc)
            if not (0.8 < dc < 1.9): continue
            if a0 is not None and abs((np.arctan2(cc[1], cc[0]) - a0 + np.pi) % (2 * np.pi) - np.pi) > ven: continue
            inl = c[np.abs(np.linalg.norm(c - cc, axis=1) - RH) < 0.05]
            if len(inl) < 5: continue
            ang = np.arctan2(*(inl - cc).T[::-1]); cob = len(np.unique(np.floor((ang + np.pi) / (np.pi / 12)))) / 24
            sc = cob * len(inl) ** 0.5
            if cob > 0.3 and sc > bs: best, bs = cc, sc
    return best, bs
res = {}
for k in ("izq", "der"):
    p = remuestrear(E[k], 0.25); T, U, W = marcos(p); th = np.full(len(p), np.nan); dc = np.full(len(p), np.nan)
    Q = []
    for i in range(len(p)):
        s_ = m.section(plane_normal=T[i], plane_origin=p[i])
        if s_ is None: Q.append(np.zeros((0, 2))); continue
        P = np.vstack(s_.discrete) - p[i]; q = np.c_[P @ U[i], P @ W[i]]; Q.append(q[np.linalg.norm(q, axis=1) < 3])
    # semilla: la mejor detección libre en las primeras 16 estaciones (la cuerda cuelga libre: sin ambigüedad)
    cand = [(ransac(Q[i]), i) for i in range(min(16, len(p)))]
    (cc0, _), i0 = max(cand, key=lambda t: t[0][1])
    th[i0] = np.arctan2(cc0[1], cc0[0]); dc[i0] = np.linalg.norm(cc0)
    for rango in (range(i0 + 1, len(p)), range(i0 - 1, -1, -1)):
        a_prev = th[i0]
        for i in rango:
            cc, sc = ransac(Q[i], a_prev, 0.45)
            if cc is not None:
                th[i] = np.arctan2(cc[1], cc[0]); dc[i] = np.linalg.norm(cc); a_prev = th[i]
    ok = np.isfinite(th); print(k, "estaciones con hebra", ok.sum(), "/", len(p))
    # continuidad: desenrollar y filtrar saltos
    t = np.unwrap(np.where(ok, th, 0)); idx = np.nonzero(ok)[0]
    tu = np.unwrap(th[idx]); med = median_filter(tu, 9, mode="nearest"); bueno = np.abs(tu - med) < 0.5
    ti = np.interp(np.arange(len(p)), idx[bueno], tu[bueno]); di = np.interp(np.arange(len(p)), idx[bueno], dc[idx][bueno])
    ti = gaussian_filter1d(ti, 3, mode="nearest"); di = gaussian_filter1d(di, 3, mode="nearest")
    hc = np.c_[di * np.cos(ti), di * np.sin(ti)]
    # reajuste del eje principal sin los puntos de la hebra
    off = np.zeros((len(p), 2))
    for i in range(len(p)):
        q = Q[i]
        if len(q) < 8: continue
        q = q[np.linalg.norm(q - hc[i], axis=1) > RH + 0.25]; c = np.zeros(2)
        for _ in range(10):
            d = np.linalg.norm(q - c, axis=1); sel = np.abs(d - RC) < 0.3
            if sel.sum() < 8: break
            qq = q[sel]; dq = np.linalg.norm(qq - c, axis=1); c = c + np.mean((qq - c) * ((dq - RC) / dq)[:, None], axis=0) * 1.5
        if np.linalg.norm(c) < 0.8: off[i] = c
    off = gaussian_filter1d(off, 2, axis=0, mode="nearest")
    print("  corrección del eje principal mm (p50, p95):", np.round(np.percentile(np.linalg.norm(off, axis=1), [50, 95]), 2))
    res[k + "_eje"] = p + U * off[:, :1] + W * off[:, 1:]
    res[k] = p + U * hc[:, :1] + W * hc[:, 1:]
    res[k + "_ok"] = ok
    print("  distancia al eje mm", np.round(np.percentile(di, [5, 50, 95]), 2), "giro total (vueltas)", round(float((ti[-1] - ti[0]) / 2 / np.pi), 2))
np.savez(out / "hebras.npz", **res)
