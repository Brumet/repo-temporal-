"""Corte por el cuello: cabeza (rojo) y cuerpo (gris) para revisar el labio de la unión.
Uso: python corte_union.py carpeta_cabeza salida.png"""
import sys, numpy as np, trimesh
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
d = Path(sys.argv[1]); out = sys.argv[2]
piezas = [(trimesh.load_mesh(d / "cuerpo.stl", process=True), "#8c8c96"), (trimesh.load_mesh(d / "cabeza.stl", process=True), "#d0705f")]
def dibuja(ax, m, fc, o, nrm, ejes):
    s = m.section(plane_origin=o, plane_normal=nrm)
    if s is None: return
    lps = [lp[:, ejes] for lp in s.discrete if len(lp) > 2]; ps = [MPath(l) for l in lps]
    V, Cd = [], []
    for i, lp in enumerate(lps):
        pr = sum(ps[j].contains_point(lp[0]) for j in range(len(lps)) if j != i)
        ar = 0.5 * np.sum(lp[:-1, 0] * lp[1:, 1] - lp[1:, 0] * lp[:-1, 1])
        if (ar > 0) != (pr % 2 == 0): lp = lp[::-1]
        V += lp.tolist(); Cd += [MPath.MOVETO] + [MPath.LINETO] * (len(lp) - 1)
    ax.add_patch(PathPatch(MPath(V, Cd), fc=fc, ec="k", lw=.3))
fig, axs = plt.subplots(1, 3, figsize=(21, 8))
for ax, (o, nrm, ejes, lim, t) in zip(axs, [([0, 0, 0], [1, 0, 0], [1, 2], ((-60, 30), (225, 305)), "Lateral x=0 (y,z)"),
                                          ([-20, 0, 0], [1, 0, 0], [1, 2], ((-60, 30), (225, 305)), "Lateral x=-20 (y,z)"),
                                          ([0, -25, 0], [0, 1, 0], [0, 2], ((-45, 45), (225, 305)), "Frontal y=-25 (x,z)")]):
    for m, fc in piezas: dibuja(ax, m, fc, o, nrm, ejes)
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_title(t)
plt.tight_layout(); plt.savefig(out, dpi=80); print("ok")
