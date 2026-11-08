"""24 vistas alrededor del cuello (12 azimuts × 2 alturas) de los a_/b_/c_*.stl de una carpeta, en un mosaico.
Uso: blender -b --python vistas24.py -- carpeta salida.png [escala]"""
import bpy, sys, os, glob, math
from mathutils import Vector
carpeta, salida = sys.argv[-2], sys.argv[-1]
esc = float(os.environ.get("ESC", "45"))
bpy.ops.wm.read_factory_settings(use_empty=True)
for f in sorted(glob.glob(carpeta + "/*.stl")):
    b = os.path.basename(f)
    if b[:2] not in ("a_", "b_", "c_"):
        continue
    bpy.ops.wm.stl_import(filepath=f); o = bpy.context.selected_objects[0]
    o.color = {"a_": (0.25, 0.55, 1.0, 1), "c_": (0.85, 0.42, 0.35, 1)}.get(b[:2], (0.72, 0.72, 0.75, 1))
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True; sc.display.shading.show_backface_culling = True
sc.render.resolution_x = sc.render.resolution_y = 500
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = esc; cam.data.clip_end = 1e4
n = Vector((0, -1, 1)).normalized(); ex = Vector((1, 0, 0)); ey = n.cross(ex)
c0 = Vector((-0.6, -25.0, 262.0)) + n * 1.5
tiles = []
for elev in (0.45, -0.45):
    for k in range(12):
        t = 2 * math.pi * k / 12
        u = math.cos(t) * ex + math.sin(t) * ey
        dirv = (u + n * elev).normalized()
        foco = c0 + u * 26
        cam.location = foco + dirv * 400
        cam.rotation_euler = (foco - cam.location).to_track_quat('-Z', 'Y').to_euler()
        p = f"{carpeta}/_v{len(tiles):02d}.png"; sc.render.filepath = p; bpy.ops.render.render(write_still=True); tiles.append(p)
print("TILES", len(tiles))
