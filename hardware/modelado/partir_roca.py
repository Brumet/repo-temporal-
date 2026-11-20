"""
Parte el cuerpo en ROCA + SUPERIOR (calavera + cuervo) para la Jupiter 2 (302 × 162 × 300 mm).
- Costura: la superficie superior de la roca, interpolada bajo la calavera → cae en el pliegue donde la calavera se apoya.
- Lo que sale por encima de esa superficie y no es la pieza superior (cristales, piedritas) vuelve a la roca.
- Unión: se rellena el hueco interior TAPON mm a cada lado de la costura (cara de contacto llena para pegar),
  canal Ø CANAL para los cables, 3 pasadores Ø3 asimétricos (5 mm por lado).
Uso: python partir_roca.py cuervo_reparado.stl cuerpo.stl salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from scipy.interpolate import griddata
from scipy import ndimage
from shapely.geometry import Polygon, Point

sol_f, cue_f, out = sys.argv[1:4]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
G, TAPON, CANAL, PIN_D, PIN_L, HOLG = 0.5, 6.0, 10.0, 3.0, 5.0, 0.15
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
sol = trimesh.load_mesh(sol_f, process=True); SOL = man(sol); CUE = man(trimesh.load_mesh(cue_f, process=True))

# huella de la calavera a z 43 (lazo mayor) dilatada 3 mm
s = sol.section(plane_normal=[0, 0, 1], plane_origin=[0, 0, 43.0])
huella = max((Polygon(q[:, :2]) for q in s.discrete if len(q) > 20), key=lambda p: p.area).buffer(0).buffer(3.0)
# altura de la cara superior de la roca fuera de la huella: rayos hacia abajo desde z 44
lo, hi = sol.bounds[0, :2] - 2, sol.bounds[1, :2] + 2
gx, gy = np.meshgrid(np.arange(lo[0], hi[0], G), np.arange(lo[1], hi[1], G), indexing="ij")
P = np.c_[gx.ravel(), gy.ravel()]
o = np.c_[P, np.full(len(P), 44.0)]
L, I, _ = sol.ray.intersects_location(o, np.tile([0, 0, -1.0], (len(o), 1)), multiple_hits=False)
Z = np.full(len(P), np.nan); Z[I] = L[:, 2]
from matplotlib.path import Path as _P
dentro = _P(np.asarray(huella.exterior.coords)).contains_points(P)
conocido = ~np.isnan(Z) & ~dentro
Zf = Z.copy()
Zf[dentro] = griddata(P[conocido], Z[conocido], P[dentro], method="linear")
Zf = np.where(np.isnan(Zf), np.nanmedian(Z[conocido]), Zf)
Zf = Zf.reshape(gx.shape)
Zf = ndimage.gaussian_filter(Zf, 1.0) * dentro.reshape(gx.shape) + Zf * (~dentro.reshape(gx.shape))
Zf = np.minimum(Zf, 43.0)
Zf = np.where(dentro.reshape(gx.shape), Zf, Zf + 0.8)        # fuera de la calavera: 0,8 mm sobre la roca (sin películas)
print("costura bajo la calavera: z", np.round(np.percentile(Zf[dentro.reshape(gx.shape)], [5, 50, 95]), 1))
# sólido "arriba de la costura": superficie de altura + paredes + tapa a z 400
nx, ny = gx.shape
Vb = np.c_[gx.ravel(), gy.ravel(), Zf.ravel()]; Vt = np.c_[gx.ravel(), gy.ravel(), np.full(nx * ny, 400.0)]
idx = np.arange(nx * ny).reshape(nx, ny); F = []
a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
F += [np.c_[a, c, b], np.c_[a, d, c]]                      # fondo (normal hacia abajo)
N = nx * ny; F += [np.c_[a + N, b + N, c + N], np.c_[a + N, c + N, d + N]]
borde = np.r_[idx[:, 0], idx[-1, 1:], idx[::-1, -1][1:], idx[0, ::-1][1:-1]]
for i in range(len(borde)):
    p0, p1 = borde[i], borde[(i + 1) % len(borde)]
    F += [np.array([[p0, p1, p1 + N], [p0, p1 + N, p0 + N]])]
arriba_t = trimesh.Trimesh(np.vstack([Vb, Vt]), np.vstack(F), process=True); trimesh.repair.fix_normals(arriba_t)
if arriba_t.volume < 0: arriba_t.invert()
ARR = man(arriba_t); print("cortador", ARR.status())
sup = CUE ^ ARR; roca = CUE - ARR
partes = sorted(sup.decompose(), key=lambda q: -q.volume())
sup = partes[0]
for q in partes[1:]: roca = roca + q                      # cristales y piedras vuelven a la roca
print("superior", round(sup.volume() / 1000, 1), "cm³ | trozos devueltos a la roca", len(partes) - 1)
# tapón: rellena el hueco a ±TAPON de la costura dentro de la huella, menos el canal de cables
hue = SOL - CUE                                            # hueco interior (y zona de tapa/encastres)
zc = float(np.median(Zf[dentro.reshape(gx.shape)]))
pts = np.asarray(huella.buffer(-1.0).exterior.coords)[:-1]
if not Polygon(pts).exterior.is_ccw: pts = pts[::-1]
prisma = mf.Manifold.extrude(mf.CrossSection([pts.tolist()]), 2 * TAPON + 6).translate([0, 0, zc - TAPON - 3])
banda = (ARR ^ prisma ^ mf.Manifold.cube([1000, 1000, 1000]).translate([-500, -500, zc - TAPON - 3]))
tap_sup = hue ^ ARR ^ prisma ^ mf.Manifold.cube([1000, 1000, TAPON + 3]).translate([-500, -500, zc - 3])
tap_inf = (hue - ARR) ^ prisma ^ mf.Manifold.cube([1000, 1000, TAPON + 3]).translate([-500, -500, zc - TAPON])
# no tapar la cavidad de la tapa/electrónica (z < 30)
tap_inf = tap_inf ^ mf.Manifold.cube([1000, 1000, 1000]).translate([-500, -500, 30.0])
hc = huella.centroid; cx, cy = hc.x, hc.y
cav = tm(hue ^ prisma ^ mf.Manifold.cube([1000, 1000, 2]).translate([-500, -500, zc + 2]))
if len(cav.vertices): cx, cy = cav.vertices[:, 0].mean(), cav.vertices[:, 1].mean()
canal = mf.Manifold.cylinder(80, CANAL / 2, CANAL / 2, 64).translate([cx, cy, zc - 40])
sup = (sup + tap_sup) - canal; roca = (roca + tap_inf) - canal
# pasadores: 3 puntos asimétricos dentro de la cara de contacto llena
contacto = tm(((tap_sup + tap_inf) - canal) ^ mf.Manifold.cube([1000, 1000, 1.0]).translate([-500, -500, zc - 0.5]))
pins = []
if len(contacto.vertices):
    C2 = contacto.vertices[:, :2]; c0 = np.array([cx, cy])
    for ang, rr in ((20, 0.75), (140, 0.62), (250, 0.7)):
        d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        proy = (C2 - c0) @ d; r = np.percentile(proy[proy > 0], 90) if (proy > 0).any() else 8
        pins.append(c0 + d * max(r * rr, CANAL / 2 + 3))
for x, y in pins:
    z0 = float(Zf[int((x - lo[0]) / G), int((y - lo[1]) / G)])
    hueco = mf.Manifold.cylinder(2 * PIN_L, (PIN_D + HOLG) / 2, (PIN_D + HOLG) / 2, 32).translate([float(x), float(y), z0 - PIN_L])
    sup = sup - hueco; roca = roca - hueco
sp = sorted(sup.decompose(), key=lambda q: -q.volume()); rp = sorted(roca.decompose(), key=lambda q: -q.volume())
print("superior piezas", [round(q.volume() / 1000, 2) for q in sp[:3]], "| roca piezas", [round(q.volume() / 1000, 2) for q in rp[:3]])
tm(sp[0]).export(out / "superior.stl"); tm(rp[0]).export(out / "roca.stl")
json.dump({"z_costura_mediana": zc, "canal": [cx, cy], "pasadores": [list(map(float, p)) for p in pins]}, open(out / "partir.json", "w"), indent=1)
