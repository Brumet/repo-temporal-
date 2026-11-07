"""
Ahueca el cuervo dejando paredes de PARED mm, sin tocar la superficie exterior.

1. Rasteriza la malla reparada en vóxeles de VOX mm (rebanadas + relleno par-impar).
2. Calcula a qué profundidad está cada vóxel (transformada de distancia).
3. Cavidad = vóxeles a más de PARED mm de la superficie, quitando cuellos de menos de
   CUELLO_MIN mm (así las patas, el pico y la cola quedan macizos: los cables van por un
   canal aparte).
4. Superficie de la cavidad con marching cubes, suavizada, y resta booleana exacta.

Uso: python ahuecar.py cuervo_reparado.stl carpeta_salida
"""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

PARED = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0   # grosor de pared (mm)
VOX = 0.5          # tamaño de vóxel (mm)
CUELLO_MIN = 5.0   # cavidades más angostas que esto se rellenan (patas, pico, cola)

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
m = trimesh.load_mesh(src, process=True)
mn, mx = m.bounds
pad = 3
nx, ny = int(np.ceil((mx[0] - mn[0]) / VOX)) + 2 * pad, int(np.ceil((mx[1] - mn[1]) / VOX)) + 2 * pad
zs = np.arange(mn[2] + VOX / 2, mx[2], VOX)
vol = np.zeros((len(zs) + 2 * pad, ny, nx), bool)
secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs.tolist())
for k, s in enumerate(secs):
    if s is None:
        continue
    T = s.metadata["to_3D"]
    acc = np.zeros((ny, nx), bool)
    for loop in s.discrete:
        if len(loop) < 3:
            continue
        p3 = trimesh.transform_points(np.column_stack([loop[:, :2], np.zeros(len(loop))]), T)
        pts = [((x - mn[0]) / VOX + pad, (y - mn[1]) / VOX + pad) for x, y in p3[:, :2]]
        img = Image.new("1", (nx, ny), 0); ImageDraw.Draw(img).polygon(pts, fill=1)
        acc ^= np.array(img)
    vol[k + pad] = acc
    if k % 100 == 0:
        print(f"rebanada {k}/{len(zs)}", flush=True)
print(f"rasterizado {time.time()-t0:.0f} s · {vol.sum()*VOX**3/1000:.0f} cm³", flush=True)

prof = ndimage.distance_transform_edt(vol, sampling=VOX).astype(np.float32)
cav = prof > PARED
# Apertura morfológica: quita cuellos angostos (patas, pico, cola) y dejar cavidades amplias
r = int(round(CUELLO_MIN / 2 / VOX))
bola = np.linalg.norm(np.mgrid[-r:r + 1, -r:r + 1, -r:r + 1], axis=0) <= r
cav = ndimage.binary_opening(cav, structure=bola)
lab, n = ndimage.label(cav)
tam = ndimage.sum(cav, lab, range(1, n + 1)) * VOX ** 3 / 1000
print("cavidades (cm³):", sorted(np.round(tam, 1), reverse=True)[:8], flush=True)
keep = np.isin(lab, [i + 1 for i, v in enumerate(tam) if v > 2.0])   # descartar burbujas < 2 cm³
# Campo suave para una superficie interior limpia
campo = ndimage.gaussian_filter(keep.astype(np.float32), 1.0)
v, f, _, _ = measure.marching_cubes(campo, 0.5, spacing=(VOX, VOX, VOX))
v = v[:, ::-1] + [mn[0] - pad * VOX, mn[1] - pad * VOX, mn[2] - pad * VOX + VOX / 2]   # (z,y,x) → (x,y,z)
f = f[:, ::-1]
cavm = trimesh.Trimesh(v, f, process=True)
cavm = cavm.simplify_quadric_decimation(face_count=min(len(cavm.faces), 400_000)) if len(cavm.faces) > 400_000 else cavm
trimesh.repair.fix_normals(cavm)
if cavm.volume < 0:
    cavm.invert()
print(f"cavidad: {len(cavm.faces):,} caras · estanca={cavm.is_watertight}", flush=True)

def man(t):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
C, H = man(m), man(cavm)
print("estado:", C.status(), H.status(), flush=True)
hueco = C - H
me = hueco.to_mesh()
res = trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
res.export(out / "cuervo_hueco.stl"); cavm.export(out / "cavidad.stl")
info = {"pared_mm": PARED, "cuello_min_mm": CUELLO_MIN, "macizo_cm3": round(C.volume() / 1000, 1),
        "hueco_cm3": round(hueco.volume() / 1000, 1), "cavidad_cm3": round(H.volume() / 1000, 1),
        "ahorro_%": round(100 * (1 - hueco.volume() / C.volume()), 1), "cavidades_cm3": sorted([round(x, 1) for x in tam if x > 2], reverse=True)}
(out / "ahuecado.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(info, indent=2, ensure_ascii=False), f"\n{time.time()-t0:.0f} s")
