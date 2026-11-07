"""Pinta el modelo de dos colores según el lado del plano de corte z - y = C (cabeza: rojizo).
La costura es la frontera de color. Uso: blender -b --python ver_corte.py -- modelo.stl salida_dir C"""
import bpy, sys, os
import numpy as np
from mathutils import Vector
stl, out, C = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=stl)
ob = bpy.context.selected_objects[0]; me = ob.data
co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
if C.endswith(".json"):            # corte curvo: h > h_borde(θ)
    import json
    B = json.load(open(C)); n = np.array(B["n"]); ex = np.array(B["ex"]); ey = np.array(B["ey"]); c0 = np.array(B["centro"])
    d = co - c0; h = d @ n; th = np.arctan2(d @ ey, d @ ex) % (2 * np.pi)
    hb = np.interp(th, B["theta"], B["h_borde"], period=2 * np.pi)
    cab = h > hb
else:
    cab = (co[:, 2] - co[:, 1]) > float(C)
col = np.where(cab[:, None], [0.85, 0.45, 0.40, 1.0], [0.72, 0.72, 0.75, 1.0]).astype(np.float32)
at = me.color_attributes.new("lado", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", col.ravel())
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'VERTEX'; sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 800
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = float(os.environ.get("ESC", "110")); cam.data.clip_end = 1e4
centro = Vector((0, -22, 265))
for n, d in {"izq": (-1, 0, 0), "der": (1, 0, 0), "frente": (0, -1, 0.2), "atras": (0, 1, 0.3)}.items():
    cam.location = centro + Vector(d).normalized() * 800
    cam.rotation_euler = (centro - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}/corte_{n}.png"; bpy.ops.render.render(write_still=True)
