"""Cortes de sección por el eje de cada ojo: cabeza (gris), inserto transparente (azul), LED (rojo).
Uso: python corte_ojos.py carpeta_ojos salida.png"""
import sys, numpy as np, trimesh
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

d = Path(sys.argv[1]); out = sys.argv[2]
sys.path.insert(0, str(Path(__file__).parent))
OJOS = {"izq": ([-17.07, -55.80, 263.99], [-0.561, -0.806, -0.188]),
        "der": ([18.72, -68.26, 267.05], [0.906, 0.060, -0.420])}
cab = trimesh.load_mesh(d / "cuervo_con_ojos.stl", process=True)
fig, axs = plt.subplots(2, 2, figsize=(14, 14))
for col, (n, (a, e)) in enumerate(OJOS.items()):
    a = np.array(a); z = np.array(e) / np.linalg.norm(e)
    ins = trimesh.load_mesh(d / f"ojo_{n}.stl", process=True)
    for row, otro in enumerate(([0, 0, 1], None)):
        # plano que contiene el eje del ojo: vertical (fila 0) y horizontal (fila 1)
        x = np.cross([0, 0, 1], z); x /= np.linalg.norm(x)
        nrm = x if row == 0 else np.cross(z, x)
        ax = axs[row, col]
        # marco común: X = eje del ojo (afuera a la derecha), Y = la otra dirección del plano
        yv = np.cross(nrm, z)
        T = np.eye(4); T[:3, :3] = np.vstack([z, yv, nrm]); T[:3, 3] = -T[:3, :3] @ a
        for m, fc in ((cab, "#9a9a9a"), (ins, "#4aa3ff")):
            s = m.section(plane_origin=a, plane_normal=nrm)
            if s is None:
                continue
            p2, _ = s.to_2D(to_2D=T)
            # relleno par-impar con todos los lazos: robusto ante polígonos que shapely no repara
            from matplotlib.path import Path as MPath
            from matplotlib.patches import PathPatch
            verts, codes = [], []
            for lp in p2.discrete:
                verts += lp.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(lp) - 1)
            if verts:
                ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec="k", lw=.3, alpha=.9))
        ax.set_xlim(-14, 8); ax.set_ylim(-11, 11)
        ax.axvline(0, color="r", lw=.6, ls="--"); ax.set_aspect("equal")
        ax.set_title(f"Ojo {n} · corte {'vertical' if row == 0 else 'horizontal'} (mm · 0 = ápice del ojo, afuera a la derecha)")
        ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(out, dpi=90)
print("ok", out)
