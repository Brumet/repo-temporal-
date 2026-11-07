"""
Encuentra el canto del collar (donde termina la correa y empieza el plumaje de la cabeza)
alrededor de todo el cuello, para cortar siguiendo esa línea y no un plano.

Coordenadas del cuello: eje n = (0,-1,1)/√2 (inclinación del collar), h = altura sobre el
plano de referencia z - y = C0, θ = ángulo alrededor del eje. Para cada θ se lanza un rayo
desde afuera hacia el eje a distintas alturas h y se mide el radio de la superficie r(h).
La correa es una banda en relieve: su canto del lado de la cabeza es donde r cae de golpe
al subir h. Resultado: h_borde(θ), suavizado, en borde_collar.json.

Uso: python borde_collar.py "forma preliminar.stl" salida.json
"""
import sys, json
import numpy as np, trimesh

C0 = 287.0
N_TH, H0, H1, DH = 360, -8.0, 10.0, 0.25
src, out = sys.argv[1], sys.argv[2]
m = trimesh.load_mesh(src, process=True)
n = np.array([0, -1, 1]) / np.sqrt(2); ex = np.array([1.0, 0, 0]); ey = np.cross(n, ex)
p0 = n * C0 / np.sqrt(2)
sec = m.section(plane_origin=p0, plane_normal=n)
centro = sec.vertices.mean(0)                     # centro del cuello en el plano de referencia
centro = centro - n * ((centro - p0) @ n)
# Solo la zona del cuello (acelera mucho los rayos)
hv = (m.triangles_center - p0) @ n
m = m.submesh([np.nonzero((hv > H0 - 6) & (hv < H1 + 6))[0]], append=True)
print("caras en la zona:", len(m.faces), flush=True)
from trimesh.ray import ray_pyembree
ri = ray_pyembree.RayMeshIntersector(m)
ths = np.linspace(0, 2 * np.pi, N_TH, endpoint=False)
hs = np.arange(H0, H1 + 1e-9, DH)
R = np.full((N_TH, len(hs)), np.nan)
origs, dirs, idx = [], [], []
for i, t in enumerate(ths):
    u = np.cos(t) * ex + np.sin(t) * ey
    for j, h in enumerate(hs):
        origs.append(centro + n * h + u * 150); dirs.append(-u); idx.append((i, j))
loc, ray_i, _ = ri.intersects_location(np.array(origs), np.array(dirs), multiple_hits=False)
for p, k in zip(loc, ray_i):
    i, j = idx[k]
    u = np.cos(ths[i]) * ex + np.sin(ths[i]) * ey
    R[i, j] = (p - centro) @ u
# Canto: máxima caída de r al subir h, buscando cerca del plano C=290 (h ≈ 2,1)
dr = np.gradient(R, DH, axis=1)
borde = np.full(N_TH, np.nan)
for i in range(N_TH):
    ok = (hs > -2.0) & (hs < 7.0) & np.isfinite(dr[i])
    if ok.sum() < 5:
        continue
    j = np.argmin(np.where(ok, dr[i], np.inf))
    if dr[i, j] < -0.6:                            # caída clara (≥ 0,6 mm por mm)
        borde[i] = hs[j]
# Rellenar huecos y suavizar en círculo
v = np.isfinite(borde)
borde = np.interp(ths, ths[v], borde[v], period=2 * np.pi)
k = 7
b2 = np.concatenate([borde[-k:], borde, borde[:k]])
med = np.array([np.median(b2[i:i + 2 * k + 1]) for i in range(N_TH)])
suave = np.convolve(np.concatenate([med[-5:], med, med[:5]]), np.ones(11) / 11, "valid")
json.dump({"C0": C0, "n": n.tolist(), "ex": ex.tolist(), "ey": ey.tolist(), "centro": centro.tolist(),
           "theta": ths.tolist(), "h_borde": suave.tolist(), "detectado_%": round(100 * v.mean(), 1)},
          open(out, "w"), indent=1)
print(f"centro {np.round(centro, 1)} · canto detectado en {100*v.mean():.0f}% de los ángulos · "
      f"h de {suave.min():.1f} a {suave.max():.1f} mm (plano C=290 sería h=2,1)")
