"""Corte por el eje del ojo: cabeza, inserto, módulo LED (PCB Ø8,9 + 5050) y cables. Exporta piezas para render.
Uso: python seccion_led.py carpeta_ojos ojo(der|izq) salida"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
d, nom, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(Mf):
    me = Mf.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
F = json.load(open(d / "ojos.json"))[nom]["marco"]
c, e, x, y = (np.array(F[k]) for k in "cexy"); zl, zp = F["zl"], F["z_pcb"]
M = np.column_stack([x, y, e, c])
cab = man(trimesh.load_mesh(d / "cabeza_ojos.stl", process=True)); ojo = man(trimesh.load_mesh(d / f"ojo_{nom}.stl", process=True)); porta = man(trimesh.load_mesh(d / f"porta_led_{nom}.stl", process=True))
loc = lambda m: m.transform(M)
pcb = loc(mf.Manifold.cylinder(1.0, 4.45, 4.45, 96).translate([0, 0, zp - 1.0]) - mf.Manifold.cube([20, 20, 5], True).translate([0, 14.2, zp]))  # caras planas
led = loc(mf.Manifold.cube([4.8, 4.9, 1.6]).translate([-2.4, -2.45, zp]))
cab_ = {k: loc(mf.Manifold.cylinder(14, 0.55, 0.55, 24).translate([-0.6, dx, zp - 1.0 - 14])) for k, dx in (("rojo", -2.2), ("blanco", 0.0), ("verde", 2.2))}
corte = loc(mf.Manifold.cube([40, 80, 80]).translate([0, -40, -40]))   # se queda x_local < 0 ... (lado de la cámara)
corte = mf.Manifold.cube([40, 80, 80]).translate([-40, -40, -40]).transform(M)
caja = mf.Manifold.sphere(16, 96).transform(M)  # solo la zona del ojo
piezas = {"cabeza": cab ^ corte ^ caja, "inserto": ojo ^ corte, "porta": porta ^ corte, "pcb": pcb ^ corte, "led": led ^ corte, **{f"cable_{k}": v ^ corte for k, v in cab_.items()}}
for k, v in piezas.items(): tm(v).export(out / f"{k}.stl")
json.dump({"c": c.tolist(), "e": e.tolist(), "x": x.tolist(), "y": y.tolist()}, open(out / "marco.json", "w"))
print("ok", {k: round(v.volume(), 1) for k, v in piezas.items()})
