"""Renderiza a_*.stl (azul) y b_*.stl (gris) de una carpeta desde 4 lados. Uso: blender -b --python ver_ply.py -- carpeta salida_prefijo"""
import bpy, sys, os
from mathutils import Vector
ply, pre = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
import glob
for f in sorted(glob.glob(ply + "/*.stl")):
    bpy.ops.wm.stl_import(filepath=f); o = bpy.context.selected_objects[0]
    o.color = (0.25, 0.55, 1.0, 1) if os.path.basename(f).startswith("a_") else ((0.85, 0.42, 0.35, 1) if os.path.basename(f).startswith("c_") else (0.72, 0.72, 0.75, 1))
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 900
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = float(os.environ.get("ESC", "75")); cam.data.clip_end = 1e4
centro = Vector((0, -22, 265))
for n, d in {"izq": (-1, 0, 0.1), "der": (1, 0, 0.1), "frente": (0, -1, 0.2), "atras": (0, 1, 0.3)}.items():
    cam.location = centro + Vector(d).normalized() * 800
    cam.rotation_euler = (centro - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{pre}_{n}.png"; bpy.ops.render.render(write_still=True)
