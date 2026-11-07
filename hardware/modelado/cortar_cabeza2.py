"""
Corte cabeza/cuerpo siguiendo la costura exacta del collar (costura.py) + unión para pegar.

1. Vóxeles de VOX mm alrededor de cabeza y cuello. Cada vóxel (material o aire) toma la etiqueta
   de la superficie más cercana: así el corte entra perpendicular desde la costura.
2. Se queda solo la región conectada más grande de cada lado (ningún trozo suelto).
3. Unión: pared de 5 mm a ≤ REF mm de la costura; labio del cuerpo (d ∈ [SKIN+HOLG, 5], ≤ LABIO mm
   dentro de la cabeza); la cabeza deja solo su piel exterior (d ≤ SKIN) sobre el labio.
4. La superficie exterior sale exacta de la malla original (intersecciones booleanas).

Uso: python cortar_cabeza2.py "forma preliminar.stl" cuervo_reparado.stl cuervo_hueco.stl borde_collar.json costura.npz salida
"""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure

VOX, REF, PARED_UNION, SKIN, HOLG, LABIO = 0.3, 12.0, 5.0, 2.5, 0.15, 5.0
f_orig, f_sol, f_hue, f_borde, f_cost, out = sys.argv[1:7]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
t0 = time.time(); T = lambda: f"{time.time()-t0:.0f} s"
B = json.load(open(f_borde)); n, ex, ey, C0 = (np.array(B[k]) for k in ("n", "ex", "ey", "centro"))
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])
def h_rel(P):
    d = P - C0
    return d @ n - np.interp(np.arctan2(d @ ey, d @ ex) % (2 * np.pi), TH, HB, period=2 * np.pi)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))

orig = trimesh.load_mesh(f_orig, process=True)
sol_t = trimesh.load_mesh(f_sol, process=True)
SOL, HUE = man(sol_t), man(trimesh.load_mesh(f_hue, process=True))
# Etiqueta de cada cara de la malla original: costura dentro de la zona, signo de h fuera
cc = orig.triangles_center
lab_cara = h_rel(cc) > 0
Z = np.load(f_cost); lab_cara[Z["zona"]] = Z["cabeza"]
print("etiquetas de caras listas", T(), flush=True)

# Caja: todo lo etiquetado cabeza + margen, y hasta REF+8 mm por debajo de la costura
sel = h_rel(sol_t.vertices) > -(REF + 8)
lo, hi = sol_t.vertices[sel].min(0) - 3, sol_t.vertices[sel].max(0) + 3
nx, ny = int(np.ceil((hi[0] - lo[0]) / VOX)), int(np.ceil((hi[1] - lo[1]) / VOX))
zs = np.arange(lo[2] + VOX / 2, hi[2], VOX)
vol = np.zeros((len(zs), ny, nx), bool)
for k, s in enumerate(sol_t.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs.tolist())):
    if s is None:
        continue
    Tm = s.metadata["to_3D"]; acc = np.zeros((ny, nx), bool)
    for loop in s.discrete:
        if len(loop) < 3:
            continue
        p3 = trimesh.transform_points(np.column_stack([loop[:, :2], np.zeros(len(loop))]), Tm)
        img = Image.new("1", (nx, ny), 0)
        ImageDraw.Draw(img).polygon([((x - lo[0]) / VOX, (y - lo[1]) / VOX) for x, y in p3[:, :2]], fill=1)
        acc ^= np.array(img)
    vol[k] = acc
print(f"vóxeles {vol.shape}", T(), flush=True)
org = lo + [0, 0, 0]                    # vóxel (k,j,i) -> punto lo + (i,j,k)*VOX (+VOX/2 en z)
def pts(idx):
    k, j, i = idx
    return np.column_stack([lo[0] + i * VOX, lo[1] + j * VOX, lo[2] + VOX / 2 + k * VOX])

prof = ndimage.distance_transform_edt(vol, sampling=VOX).astype(np.float32)
sup = vol & ~ndimage.binary_erosion(vol)
iz = np.nonzero(sup)
en_caja = np.all((cc > lo - 2) & (cc < hi + 2), axis=1)
arbol = cKDTree(cc[en_caja])
_, near = arbol.query(pts(iz), workers=-1)
lab_sup = lab_cara[en_caja][near]
L = np.zeros(vol.shape, np.int8)       # 1 cuerpo, 2 cabeza (en superficie)
L[iz] = np.where(lab_sup, 2, 1)
del arbol
_, ind = ndimage.distance_transform_edt(L == 0, return_indices=True)
H = (L[tuple(ind)] == 2); del ind
print("etiquetas propagadas", T(), flush=True)
# Una sola región por lado
for lado in (True, False):
    lb, nn = ndimage.label(H == lado)
    if nn > 1:
        tam = np.bincount(lb.ravel()); tam[0] = 0
        H[(lb > 0) & (lb != np.argmax(tam))] = not lado
        print(f"{'cabeza' if lado else 'cuerpo'}: {nn - 1} trozos sueltos reasignados", flush=True)
distB = ndimage.distance_transform_edt(H, sampling=VOX).astype(np.float32)    # en cabeza: distancia al cuerpo
distH = ndimage.distance_transform_edt(~H, sampling=VOX).astype(np.float32)   # en cuerpo: distancia a la cabeza


def malla(mask, suave=0.5):
    campo = ndimage.gaussian_filter(np.pad(mask, 2).astype(np.float32), suave)
    v, f, _, _ = measure.marching_cubes(campo, 0.5, spacing=(VOX, VOX, VOX))
    v = v[:, ::-1] + (lo - 2 * VOX + [0, 0, VOX / 2])
    t = trimesh.Trimesh(v, f[:, ::-1], process=True)
    trimesh.repair.fix_normals(t)
    if t.volume < 0:
        t.invert()
    return man(t)


def malla_campo(campo, suave=1.0):
    """Superficie suave (subvóxel) en campo = 0, con campo > 0 adentro."""
    c = ndimage.gaussian_filter(np.pad(campo, 2, constant_values=-10), suave)
    v, f, _, _ = measure.marching_cubes(c, 0.0, spacing=(VOX, VOX, VOX))
    v = v[:, ::-1] + (lo - 2 * VOX + [0, 0, VOX / 2])
    t = trimesh.Trimesh(v, f[:, ::-1], process=True)
    trimesh.repair.fix_normals(t)
    if t.volume < 0:
        t.invert()
    return man(t)


aire_o_pared = prof <= PARED_UNION
# Superficie de corte: campo con signo (distancia al cuerpo - distancia a la cabeza) -> sin escalones
R_cab = malla_campo(distB - distH)
R_thick_cab = malla(H & aire_o_pared & (distB <= REF)) ^ R_cab
R_thick_cue = malla(~H & aire_o_pared & (distH <= REF)) - R_cab
R_bolsillo = malla(H & (prof > SKIN) & (distB <= LABIO + 0.2))
R_labio = malla(H & (prof >= SKIN + HOLG) & (prof <= PARED_UNION) & (distB <= LABIO))
print("regiones", T(), flush=True)
cabeza = (HUE ^ R_cab) + (SOL ^ R_thick_cab) - R_bolsillo
cuerpo = (HUE - R_cab) + (SOL ^ R_thick_cue) + R_labio
print("booleanas", T(), flush=True)


def guarda(mm, nombre):
    me = mm.to_mesh()
    trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False).export(out / nombre)


partes = lambda mm: sorted([round(p.volume() / 1000, 3) for p in mm.decompose()], reverse=True)
pc, pb = partes(cabeza), partes(cuerpo)
guarda(cabeza, "cabeza.stl"); guarda(cuerpo, "cuerpo.stl")
info = {"cabeza_cm3": round(cabeza.volume() / 1000, 1), "cuerpo_cm3": round(cuerpo.volume() / 1000, 1),
        "piezas_cabeza_cm3": pc[:5], "piezas_cuerpo_cm3": pb[:5],
        "piezas_cabeza_mayores_0.01": sum(p > 0.01 for p in pc), "piezas_cuerpo_mayores_0.01": sum(p > 0.01 for p in pb)}
(out / "corte.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(info, indent=2, ensure_ascii=False), T())
