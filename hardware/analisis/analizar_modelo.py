"""
Análisis estructural del modelo del cuervo para diseñar el interior.

Corta el STL en rebanadas horizontales cada 1 mm, rasteriza cada rebanada a 0,5 mm
y calcula, con la transformada de distancia, a qué profundidad está cada punto del
material. Con eso responde:
  - grosor de cada pata y del cuello (¿cabe un canal de cables?)
  - dónde está la sección más angosta entre cuerpo y cabeza (corte de la cabeza)
  - cuánto material queda si se vacía con paredes de 3 mm (ahorro de resina)

Uso: python analizar_modelo.py "ruta/al/modelo.stl" [salida]
"""
import json, sys, time
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage

stl = Path(sys.argv[1]); out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "resultados")
out.mkdir(parents=True, exist_ok=True)
DZ, PX, PARED = 1.0, 0.5, 3.0
t0 = time.time()
m = trimesh.load_mesh(stl, process=False)
print(f"cargado {len(m.faces):,} caras en {time.time()-t0:.0f} s", flush=True)
mn, mx = m.bounds
info = {"caras": int(len(m.faces)), "min_mm": mn.round(1).tolist(), "max_mm": mx.round(1).tolist(),
        "dim_mm": (mx - mn).round(1).tolist(), "estanco": bool(m.is_watertight)}
print(info, flush=True)

nx, ny = int(np.ceil((mx[0] - mn[0]) / PX)) + 4, int(np.ceil((mx[1] - mn[1]) / PX)) + 4
zs = np.arange(mn[2] + DZ / 2, mx[2], DZ)
vol = np.zeros((len(zs), ny, nx), bool)
secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs.tolist())
for k, s in enumerate(secs):
    if s is None:
        continue
    img = Image.new("1", (nx, ny), 0); d = ImageDraw.Draw(img)
    # Relleno par-impar: cada lazo cerrado alterna dentro/fuera (sirve aunque la malla tenga detalles sueltos)
    T = s.metadata["to_3D"]
    for loop in s.discrete:
        p3 = trimesh.transform_points(np.column_stack([loop[:, :2], np.zeros(len(loop))]), T)
        pts = [((x - mn[0]) / PX + 2, (y - mn[1]) / PX + 2) for x, y in p3[:, :2]]
        if len(pts) >= 3 and np.allclose(loop[0], loop[-1], atol=0.05):   # solo lazos cerrados
            tmp = Image.new("1", (nx, ny), 0); ImageDraw.Draw(tmp).polygon(pts, fill=1)
            img = Image.fromarray(np.logical_xor(np.array(img), np.array(tmp)))
    vol[k] = np.array(img)
    if k % 50 == 0:
        print(f"rebanada {k}/{len(zs)}  z={zs[k]:.0f} mm", flush=True)
print(f"rasterizado en {time.time()-t0:.0f} s", flush=True)

prof = ndimage.distance_transform_edt(vol, sampling=(DZ, PX, PX)).astype(np.float32)   # profundidad dentro del material (mm)
vox = DZ * PX * PX
info["volumen_macizo_cm3"] = round(float(vol.sum() * vox / 1000), 1)
info["volumen_hueco_3mm_cm3"] = round(float((vol & (prof <= PARED)).sum() * vox / 1000), 1)
info["ahorro_%"] = round(100 * (1 - info["volumen_hueco_3mm_cm3"] / info["volumen_macizo_cm3"]), 1)

# Por altura: número de piezas separadas y el grosor máximo (2 × profundidad máxima) de cada una
filas = []
for k, z in enumerate(zs):
    lab, n = ndimage.label(vol[k])
    piezas = []
    for i in range(1, n + 1):
        msk = lab == i
        area = msk.sum() * PX * PX
        if area < 4:            # ignorar plumitas y detalles de menos de 4 mm²
            continue
        ys, xs = np.nonzero(msk)
        # grosor 2D de la rebanada: lo que importa para pasar un cable horizontal
        d2 = ndimage.distance_transform_edt(np.pad(msk, 1)) * PX
        piezas.append({"area_mm2": round(float(area), 1), "grosor_mm": round(float(2 * d2.max()), 1),
                       "cx": round(float(xs.mean() * PX + mn[0] - 2 * PX), 1), "cy": round(float(ys.mean() * PX + mn[1] - 2 * PX), 1)})
    piezas.sort(key=lambda p: -p["area_mm2"])
    filas.append({"z": round(float(z), 1), "piezas": piezas})
(out / "rebanadas.json").write_text(json.dumps(filas, indent=0), encoding="utf-8")
(out / "resumen.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
np.save(out / "profundidad.npy", prof.astype(np.float16))
json.dump({"mn": mn.tolist(), "dz": DZ, "px": PX}, open(out / "rejilla.json", "w"))
print(json.dumps(info, indent=2, ensure_ascii=False))
for f in filas[::5]:
    print(f["z"], [(p["area_mm2"], p["grosor_mm"]) for p in f["piezas"][:5]])
print(f"listo en {time.time()-t0:.0f} s")
