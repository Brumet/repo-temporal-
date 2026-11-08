"""
Tapa inferior de la roca + soportes internos.

- TAPA (z 0-3): reemplaza el piso de la roca; contorno interior de la pared -1 mm (holgura 0,3).
  Asienta contra una REPISA interior de 5 mm (z 3-6). 2 tornillos avellanados (3x12 para plastico) a 2 bosses;
  4 rebajes para patas de goma de 10 mm (dos tapan los tornillos). Ranuras de ventilacion bajo la ESP32.
  BANDEJA DE LASTRE encima (paredes de 2 mm, 22 mm de alto) para yeso o cemento.
- ESP32-C3 en un estante pegado a la pared de atras (+y), USB-C saliendo por un agujero 13 x 7,5.
- SWITCH MX en el costado (+x): la tecla es un pedazo de la roca (0,2 mm de holgura por lado) con encastre de
  cruz MX por dentro; torre-guia y placa de 1,5 mm con agujero 14x14 (el switch entra por el agujero de la tecla).
Uso: python roca_tapa.py cuerpo.stl salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from shapely.geometry import Polygon, Point

cue_f, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


def sec(poly):
    pts = np.asarray(poly.exterior.coords)[:-1]
    if not Polygon(pts).exterior.is_ccw: pts = pts[::-1]
    return mf.CrossSection([pts.tolist()])


def prisma(poly, z0, z1): return mf.Manifold.extrude(sec(poly), z1 - z0).translate([0, 0, z0])
def cil(x, y, r, z0, z1, n=48): return mf.Manifold.cylinder(z1 - z0, r, r, n).translate([float(x), float(y), z0])
def caja(x0, x1, y0, y1, z0, z1): return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


T_TAPA, HOLG, REPISA, Z_REP = 3.0, 0.3, 5.0, 3.0
cue_t = trimesh.load_mesh(cue_f, process=True); CUE = man(cue_t)
s = cue_t.section(plane_normal=[0, 0, 1], plane_origin=[0, 0, 8])
lazos = [Polygon(q[:, :2]) for q in s.discrete if len(q) > 50]
interior = min(lazos, key=lambda p: p.area).buffer(0).simplify(0.2)          # cara interior de la pared
c0 = np.array(interior.centroid.coords[0])
info = {"area_interior_cm2": round(interior.area / 100, 1)}

# ---------------- cuerpo: quitar piso, repisa, bosses
tapa_poly = interior.buffer(-1.0 - HOLG, join_style=2)
hueco_piso = prisma(interior.buffer(-1.0, join_style=2), -1, T_TAPA)
repisa = prisma(interior, Z_REP, Z_REP + 3) - prisma(interior.buffer(-REPISA, join_style=2), Z_REP - 1, Z_REP + 4)


def en_pared(ang, dentro):
    """Punto a 'dentro' mm hacia el centro desde la cara interior de la pared, en el angulo dado."""
    d = np.array([np.cos(ang), np.sin(ang)]); r = 0.0
    while interior.contains(Point(*(c0 + d * (r + 0.5)))): r += 0.5
    return c0 + d * (r - dentro)


TORN = [en_pared(np.radians(-90), 4.5), en_pared(np.radians(150), 4.5)]
bosses = mf.Manifold()
for x, y in TORN: bosses = bosses + cil(x, y, 5.0, Z_REP, 16)
bosses = bosses ^ prisma(interior.buffer(0.5), 0, 20)

# ---------------- ESP32: estante contra la pared de atras
from shapely.geometry import LineString
y_in = float(interior.intersection(LineString([(0, -300), (0, 300)])).bounds[3])   # cara interior de la pared de atras en x=0
PCB_W, PCB_L, USB_SALE, Z_PCB = 18.1, 22.8, 1.4, 7.0
yb = y_in - USB_SALE                                   # borde trasero del PCB (el USB llega a la cara interior)
estante = caja(-13.5, 13.5, yb - PCB_L - 3, y_in + 1, Z_REP, Z_PCB) - caja(-PCB_W / 2 - 0.2, PCB_W / 2 + 0.2, yb - PCB_L - 0.2, yb + 0.2, Z_PCB - 1.0, Z_PCB + 1)
estante = estante ^ prisma(interior.buffer(1.0), 0, 20)
z_usb = Z_PCB - 1.0 + 1.0 + 1.6                         # PCB en el bolsillo (1 mm) + grosor + medio conector
usb = mf.Manifold.cube([13, 20, 7.5], True).translate([0, y_in + 5, z_usb])

# ---------------- SWITCH en el costado +x, a media altura
z_bt = 19.0
pc = np.array([interior.bounds[2] - 3.0, c0[1], z_bt])                     # dentro, cerca de la pared +x
cc = cue_t.triangles_center; nn = cue_t.face_normals
zona = (np.linalg.norm(cc[:, :2] - pc[:2], axis=1) < 14) & (np.abs(cc[:, 2] - z_bt) < 8) & (cc[:, 0] > pc[0] + 1)
n_ = (nn[zona] * cue_t.area_faces[zona, None]).sum(0); n_[2] = 0; n_ /= np.linalg.norm(n_)
L, I, _ = cue_t.ray.intersects_location([pc], [n_], multiple_hits=True)
sup = L[np.argmax((L - pc) @ n_)]                    # la interseccion mas externa = superficie de la roca
u = np.cross([0, 0, 1], n_); u /= np.linalg.norm(u); v = np.array([0, 0, 1.0])
Mb = np.column_stack([u, v, -n_, sup])                 # z local = profundidad hacia dentro
TEC, GAP, D_PLACA, T_PLACA = 16.0, 0.2, 12.8, 1.5


def bx(a, b, z0, z1): return mf.Manifold.cube([a, b, z1 - z0]).translate([-a / 2, -b / 2, z0]).transform(Mb)


# contorno de la tecla: fragmento irregular de roca (no un cuadrado), ~18 mm
ANG = np.radians([8, 62, 118, 172, 228, 292]); RAD = [9.6, 8.7, 10.1, 9.0, 9.9, 8.5]
FRAG = Polygon([(r * np.cos(a), r * np.sin(a)) for a, r in zip(ANG, RAD)])


def fr(off, z0, z1):
    pts = np.asarray(FRAG.buffer(off, join_style=2).exterior.coords)[:-1]
    if not Polygon(pts).exterior.is_ccw: pts = pts[::-1]
    return mf.Manifold.extrude(mf.CrossSection([pts.tolist()]), z1 - z0).translate([0, 0, z0]).transform(Mb)


agujero_tecla = fr(GAP, -6, 3.6)
torre = (fr(GAP + 2.3, 2.0, D_PLACA + T_PLACA) - fr(0.3, 1.0, D_PLACA)
         - bx(14.0, 14.0, D_PLACA - 1, D_PLACA + T_PLACA + 1))
tecla_roca = CUE ^ fr(0.0, -6, 3.6)
cruz = bx(4.1, 1.35, 3.0, 6.7) + bx(1.35, 4.1, 3.0, 6.7)
boss_t = mf.Manifold.cylinder(6.6 - 2.5, 2.8, 2.8, 40).translate([0, 0, 2.5]).transform(Mb)
tecla = max(((tecla_roca + boss_t) - cruz).decompose(), key=lambda q: q.volume())

cuerpo = (CUE - hueco_piso) + repisa + bosses + estante + torre
cuerpo = cuerpo - usb - agujero_tecla
for x, y in TORN: cuerpo = cuerpo - cil(x, y, 1.25, Z_REP - 1, 15)

# ---------------- tapa
tapa = prisma(tapa_poly, 0, T_TAPA)
for x, y in TORN:
    tapa = (tapa - cil(x, y, 1.7, -1, 4) - mf.Manifold.cylinder(1.6, 3.4, 1.7, 40).translate([float(x), float(y), -0.01])
            - cil(x, y, 5.3, -1, 0.6))
PATAS = [en_pared(np.radians(30), 9), en_pared(np.radians(-150), 9)]
for x, y in PATAS: tapa = tapa - cil(x, y, 5.3, -1, 0.6)
for i in range(6):     # ventilacion bajo la ESP32
    xv = -10 + 4 * i; tapa = tapa - caja(xv - 1, xv + 1, yb - PCB_L, yb - 4, -1, 4)
# bandeja de lastre (deja libre la zona de la ESP32 y los tornillos)
band_poly = interior.buffer(-12, join_style=2).difference(Polygon([(-40, yb - PCB_L - 10), (40, yb - PCB_L - 10), (40, 300), (-40, 300)]))
for x, y in TORN: band_poly = band_poly.difference(Point(x, y).buffer(10))
p_sw = sup - n_ * 22.0                                   # fondo del switch + pines + cables
band_poly = band_poly.difference(LineString([tuple(sup[:2]), tuple(p_sw[:2])]).buffer(16))
band_poly = max(getattr(band_poly, "geoms", [band_poly]), key=lambda p: p.area).buffer(-0.5).buffer(0.5)
H_B = 22.0
bandeja = prisma(band_poly, T_TAPA - 0.01, T_TAPA + H_B) - prisma(band_poly.buffer(-2.0), T_TAPA, T_TAPA + H_B + 1)
tapa = tapa + bandeja
vol_lastre = band_poly.buffer(-2.0).area * H_B / 1000
info.update({"tornillos_xy": [np.round(p, 1).tolist() for p in TORN], "patas_xy": [np.round(p, 1).tolist() for p in TORN + PATAS],
             "boton_superficie": np.round(sup, 1).tolist(), "boton_eje": np.round(n_, 2).tolist(), "usb_z": z_usb, "usb_y": round(y_in, 1),
             "lastre_cm3": round(vol_lastre), "lastre_g_yeso": round(vol_lastre * 1.1), "lastre_g_cemento": round(vol_lastre * 2.0)})
cb = sorted(cuerpo.decompose(), key=lambda q: -q.volume())
print("cuerpo piezas", [round(q.volume(), 1) for q in cb[:4]], "tapa", round(tapa.volume(), 1), "tecla", round(tecla.volume(), 1), flush=True)
tm(cb[0]).export(out / "cuerpo.stl"); tm(tapa).export(out / "tapa.stl"); tm(tecla).export(out / "tecla.stl")
json.dump(info, open(out / "tapa.json", "w"), indent=1); print(json.dumps(info))
