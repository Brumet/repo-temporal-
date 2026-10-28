"""Máscara oni — v1: volúmenes principales.

Construye la máscara como campo de distancia, la vacía en cáscara, la abre
por detrás y la convierte en malla (marching cubes). Salida: export/mascara_v1.ply/.stl
Uso: python modelo_v1.py [paso_mm]
"""
import sys, os, time
import numpy as np
from skimage import measure
import trimesh
from sdf import Grid, ellipsoid, rbox, round_cone, horn, frame

STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
OUT = os.path.join(os.path.dirname(__file__), "..", "export")
rng = np.random.default_rng(7)
t0 = time.time()

g = Grid((-118, -128, -150), (118, 70, 295), STEP)
S = (-1, 1)  # -1 = izquierda del espectador (lado derecho del personaje)

# ---------------- 1. volumen base ----------------
g.add(ellipsoid((0, 5, 25), (72, 78, 85)))                    # cráneo / frente
g.add(ellipsoid((0, -20, -55), (52, 55, 75)), k=25)           # cara larga y mandíbula
g.add(round_cone((0, -73, 30), (0, -62, 92), 4.5, 3), k=5)     # cresta central de la frente

# ---------------- 2. cejas en V (enfado) ----------------
for s in S:
    u = (np.cos(np.radians(22)), 0, s * np.sin(np.radians(22)))
    g.add(ellipsoid((s * 27, -71, 18), (31, 11, 10), frame(u)), k=6)
    # remate puntiagudo hacia la sien
    g.add(round_cone((s * 40, -66, 24), (s * 62, -45, 38), 6, 1.5), k=4)

# ---------------- 3. pómulos en capas escalonadas ----------------
for s in S:
    for i, (z, y, rx, rz) in enumerate([(-16, -53, 23, 12), (-33, -51, 21, 10), (-48, -49, 18, 9)]):
        u = (np.cos(np.radians(-15)), 0, s * np.sin(np.radians(-15)))
        g.add(ellipsoid((s * (40 - 2 * i), y, z), (rx, 13, rz), frame(u)), k=2.5)

# ---------------- 4. nariz en pico ----------------
g.add(round_cone((0, -74, 20), (0, -95, -26), 7.5, 5), k=6)     # puente
g.add(ellipsoid((0, -93, -29), (9, 9, 7)), k=4)                  # punta ganchuda
for s in S:
    g.add(ellipsoid((s * 9, -80, -30), (7, 8, 6)), k=4)          # aletas

# ---------------- 5. mentón en capas ----------------
for i, (z, y, rx) in enumerate([(-86, -63, 29), (-99, -60, 24), (-112, -56, 19), (-123, -50, 14)]):
    g.add(ellipsoid((0, y, z), (rx, 13, 8)), k=2.5)

# ---------------- 6. aletas de las sienes ----------------
for s in S:
    g.add(ellipsoid((s * 69, -12, 40), (7, 32, 30), frame((0, 1, 0.35))), k=6)
    g.add(round_cone((s * 72, -30, 70), (s * 78, 15, 92), 6, 2), k=5)

# ---------------- 7. cavidades (antes de vaciar) ----------------
for s in S:
    u = (np.cos(np.radians(18)), 0, s * np.sin(np.radians(18)))
    g.sub(ellipsoid((s * 27, -80, 3), (21, 28, 11), frame(u)), k=4)   # cuencas
    g.sub(ellipsoid((s * 6, -86, -37), (3.5, 8, 3)), k=1.5)           # fosas nasales
g.sub(rbox((0, -78, -62), (33, 16, 9.5), 3), k=2)                     # ranura de la boca

# ---------------- 8. vaciado en cáscara y apertura trasera ----------------
WALL = 4.0
solid = g.D.copy()
g.D = np.maximum(solid, -(solid + WALL))
X, Y, Z = g.axes()
g.D = np.maximum(g.D, (Y[None, :, None] - 12).astype(np.float32))      # abierta por detrás
del solid

# agujeros pasantes de los ojos y fondo de la boca
for s in S:
    u = (np.cos(np.radians(18)), 0, s * np.sin(np.radians(18)))
    g.sub(ellipsoid((s * 27, -55, 2), (13, 40, 5.5), frame(u)), k=1.5)
g.sub(rbox((0, -55, -62), (27, 30, 2.2), 1.5), k=1)

# ---------------- 9. dientes ----------------
def arco(x):  # frente de la boca
    return -72 + 0.011 * x * x

for fila, z0, dx in (("sup", -57.5, 0.0), ("inf", -66.5, 4.0)):
    for x in np.linspace(-29, 29, 8) + dx:
        if abs(x) > 31: continue
        h = 4.6 * (1 + rng.uniform(-0.25, 0.3))
        w = 3.3 * (1 + rng.uniform(-0.2, 0.2))
        yaw = np.arctan(0.022 * x)
        R = frame((np.cos(yaw), np.sin(yaw), rng.uniform(-0.08, 0.08)))
        zc = z0 - (h - 4.6) * (1 if fila == "sup" else -1)
        g.add(rbox((x, arco(x) + 4, zc), (w, 4.5, h), 1.0, R), k=0.8)

# ---------------- 10. cuernos ----------------
# A: media luna fina a la izquierda del espectador, con púa interior
segsA, bbA, ptsA, radA = horn((-30, -47, 76), (-82, -58, 118), (-100, -72, 222), (-58, -80, 285), 12.5, 0.7)
g.add((segsA, bbA), k=7)
iA = int(0.45 * len(ptsA))
g.add(round_cone(ptsA[iA], ptsA[iA] + np.array([22, -6, 14]), radA[iA] * 0.55, 0.5), k=3)
# B: fino y muy alto, desde lo alto de la frente
segsB, bbB, _, _ = horn((-8, -52, 90), (-26, -60, 160), (-34, -64, 225), (-14, -60, 272), 10.5, 0.6)
g.add((segsB, bbB), k=7)
# C: grueso, a la derecha del espectador, con la punta vuelta hacia dentro
segsC, bbC, _, _ = horn((30, -44, 78), (56, -54, 128), (44, -62, 186), (8, -70, 208), 19, 1.0, power=1.1)
g.add((segsC, bbC), k=9)

print(f"campo listo en {time.time()-t0:.1f}s")

# ---------------- malla ----------------
verts, faces, normals, _ = measure.marching_cubes(g.D, 0.0, spacing=(STEP,) * 3)
verts += g.lo
mesh = trimesh.Trimesh(verts, faces, process=True)
parts = mesh.split(only_watertight=False)
mesh = max(parts, key=lambda m: len(m.faces))            # quita islas sueltas
trimesh.smoothing.filter_taubin(mesh, iterations=6)
os.makedirs(OUT, exist_ok=True)
mesh.export(os.path.join(OUT, "mascara_v1.ply"))
mesh.export(os.path.join(OUT, "mascara_v1.stl"))
ext = mesh.bounds[1] - mesh.bounds[0]
print(f"malla: {len(mesh.faces)/1e6:.2f} M caras, estanca={mesh.is_watertight}, "
      f"tamaño {ext.round(1)} mm, total {time.time()-t0:.1f}s")
