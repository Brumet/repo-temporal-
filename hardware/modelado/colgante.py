"""
Separa el colgante del pecho (dos cuerdas + nudo + punta triangular), que cuelga libre por
delante de las patas, para imprimirlo aparte.

El colgante está suelto del cuerpo por debajo de z ≈ 208 (análisis de rebanadas). Se corta a
Z_CORTE, donde las dos cuerdas son casi verticales: el corte queda perpendicular a la cuerda y
es un círculo de ~3 mm, fácil de disimular. En cada cuerda: agujero para un pin de alambre
(Ø PIN) en las dos caras, para alinear y pegar.

Uso: python colgante.py cuerpo.stl salida_dir
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

# Plano por el canto superior de los dos amarres que sujetan la punta (izq z≈194,8 · der z≈195,9)
P_IZQ, P_DER = np.array([-7.2, -37.4, 194.8]), np.array([13.7, -35.8, 195.9])
N_CORTE = np.array([-(P_DER[2] - P_IZQ[2]) / (P_DER[0] - P_IZQ[0]), 0, 1.0]); N_CORTE /= np.linalg.norm(N_CORTE)
P0 = (P_IZQ + P_DER) / 2
Z_CORTE = float(P0[2])
PIN, PROF_PIN, HOLG = 1.0, 3.0, 0.08
CAJA = dict(x=(-25.0, 25.0), y=(-48.0, -31.0), z=(150.0, 215.0))
CUERDAS = [(-7.2, -37.4), (13.7, -35.8)]

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
t = trimesh.load_mesh(src, process=True)
man = lambda m: mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
C = man(t)
lo = [CAJA["x"][0], CAJA["y"][0], CAJA["z"][0]]; hi = [CAJA["x"][1], CAJA["y"][1], CAJA["z"][1]]
caja = mf.Manifold.cube([h - l for l, h in zip(lo, hi)]).translate(lo)
ex_ = np.cross([0, 1.0, 0], N_CORTE); ex_ /= np.linalg.norm(ex_); ey_ = np.cross(N_CORTE, ex_)
Mp = np.column_stack([ex_, ey_, N_CORTE, P0])
bajo = mf.Manifold.cube([400, 400, 200]).translate([-200, -200, -200]).transform(Mp)   # semiespacio bajo el plano
colg = C ^ caja ^ bajo
partes = sorted(colg.decompose(), key=lambda p: -p.volume())
print("trozos en la caja (mm³):", [round(p.volume(), 1) for p in partes[:6]])
colg = partes[0]
# Centrar cada cuerda en la sección real del corte
sec = tm(colg).section(plane_origin=P0 - N_CORTE * 0.05, plane_normal=N_CORTE)
centros = []
for x0, y0 in CUERDAS:
    best = None
    for lp in sec.discrete:
        c = lp.mean(0)
        if np.hypot(c[0] - x0, c[1] - y0) < 5 and (best is None or len(lp) > len(best)):
            best = lp
    c = best.mean(0) if best is not None else np.array([x0, y0, Z_CORTE])
    ancho = (best[:, :2].max(0) - best[:, :2].min(0)).min() if best is not None else None
    centros.append((float(c[0]), float(c[1]), None if ancho is None else round(float(ancho), 2)))
print("cuerdas en el corte (x, y, ancho mm):", centros)
def pin(x, y, d0, d1, r):
    q = np.array([x, y, 0.0]); q[2] = P0[2] - (N_CORTE[0] * (x - P0[0])) / N_CORTE[2]   # punto sobre el plano
    M = np.column_stack([ex_, ey_, N_CORTE, q])
    return mf.Manifold.cylinder(d1 - d0, r, r, 48).translate([0, 0, d0]).transform(M)
agujeros_c = mf.Manifold()
agujeros_b = mf.Manifold()
for x, y, _ in centros:
    agujeros_c += pin(x, y, -PROF_PIN, 1, PIN / 2 + HOLG)
    agujeros_b += pin(x, y, -1, PROF_PIN, PIN / 2 + HOLG)
colgante = colg - agujeros_c
cuerpo = (C - colg) - agujeros_b
pc = sorted([round(p.volume(), 1) for p in colgante.decompose()], reverse=True)
pb = sorted([round(p.volume() / 1000, 2) for p in cuerpo.decompose()], reverse=True)
tm(colgante).export(out / "colgante.stl"); tm(cuerpo).export(out / "cuerpo_sin_colgante.stl")
info = {"plano": {"punto": P0.round(2).tolist(), "normal": N_CORTE.round(4).tolist()}, "cuerdas": centros, "pin_mm": PIN, "colgante_mm3": round(colgante.volume(), 1),
        "piezas_colgante_mm3": pc[:4], "piezas_cuerpo_cm3": pb[:4],
        "colgante_caja_mm": np.round(np.array(colgante.bounding_box()), 1).tolist()}
(out / "colgante.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print(json.dumps(info, indent=2))
