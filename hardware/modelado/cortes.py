"""Cortes generales de una malla: lateral (x=cte), frontal (y=cte) y horizontales (z=cte).
Uso: python cortes.py malla.stl salida.png [x] [y] [z1,z2,...]"""
import sys, numpy as np, trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

src, out = sys.argv[1], sys.argv[2]
X = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
Y = float(sys.argv[4]) if len(sys.argv) > 4 else -15.0
ZS = [float(z) for z in sys.argv[5].split(",")] if len(sys.argv) > 5 else [20, 90, 155, 200, 262]
m = trimesh.load_mesh(src, process=True)


def dibuja(ax, origen, normal, ejes, titulo):
    s = m.section(plane_origin=origen, plane_normal=normal)
    if s is not None:
        verts, codes = [], []
        lps = [lp[:, ejes] for lp in s.discrete if len(lp) > 2]
        paths = [MPath(lp) for lp in lps]
        for i, lp in enumerate(lps):
            prof = sum(paths[j].contains_point(lp[0]) for j in range(len(lps)) if j != i)
            area = 0.5 * np.sum(lp[:-1, 0] * lp[1:, 1] - lp[1:, 0] * lp[:-1, 1])
            if (area > 0) != (prof % 2 == 0):   # exteriores antihorario, huecos horario
                lp = lp[::-1]
            verts += lp.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(lp) - 1)
        ax.add_patch(PathPatch(MPath(verts, codes), fc="#7d7d86", ec="k", lw=.25))
    ax.autoscale_view(); ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_title(titulo, fontsize=10)


fig = plt.figure(figsize=(18, 12))
a1 = fig.add_subplot(1, 3, 1); dibuja(a1, [X, 0, 0], [1, 0, 0], [1, 2], f"Lateral x={X:g} (y, z)"); a1.set_xlim(-100, 125); a1.set_ylim(-5, 305)
a2 = fig.add_subplot(1, 3, 2); dibuja(a2, [0, Y, 0], [0, 1, 0], [0, 2], f"Frontal y={Y:g} (x, z)"); a2.set_xlim(-95, 95); a2.set_ylim(-5, 305)
sub = fig.add_gridspec(len(ZS), 3)[:, 2]
gs = sub.subgridspec(len(ZS), 1)
for i, z in enumerate(ZS):
    ax = fig.add_subplot(gs[i]); dibuja(ax, [0, 0, z], [0, 0, 1], [0, 1], f"z={z:g}")
plt.tight_layout(); plt.savefig(out, dpi=80); print("ok", out)
