"""Primeros planos de cada ojo mirando de frente, con cuadrícula en mm (coordenadas de cámara).
Uso: blender -b --python vista_ojos.py -- modelo.stl salida"""
import bpy, sys
from mathutils import Vector

stl, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=stl)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'SINGLE'; sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 30; cam.data.clip_end = 1e4
dg = bpy.context.evaluated_depsgraph_get()
for nombre, sx in (("izq", -1), ("der", 1)):
    ok, loc, nor, *_ = sc.ray_cast(dg, Vector((sx * 200, -64, 268)), Vector((-sx, 0, 0)))
    cam.location = loc + nor * 200
    q = (-nor).to_track_quat('-Z', 'Z'); cam.rotation_euler = q.to_euler()
    m = cam.matrix_world
    print("OJO", nombre, "punto", tuple(round(v, 2) for v in loc), "normal", tuple(round(v, 3) for v in nor),
          "derecha_cam", tuple(round(v, 3) for v in (m.to_3x3() @ Vector((1, 0, 0)))),
          "arriba_cam", tuple(round(v, 3) for v in (m.to_3x3() @ Vector((0, 1, 0)))))
    sc.render.filepath = f"{out}/ojo_{nombre}.png"
    bpy.ops.render.render(write_still=True)
