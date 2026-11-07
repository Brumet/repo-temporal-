"""
Vistas ortográficas con cuadrícula en mm para ubicar el collar, el cuello y las patas.
Uso: blender -b --python vistas.py -- "modelo.stl" carpeta_salida
"""
import bpy, sys
from mathutils import Vector

stl, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=stl)
ob = bpy.context.selected_objects[0]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'SINGLE'
sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 900
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.clip_end = 1e5

# (nombre, centro, dirección de la cámara, ancho de la vista en mm)
vistas = [
    ("cuello_frente", (-2, -40, 245), (0, -1, 0), 120),
    ("cuello_lado",   (-2, -30, 245), (-1, 0, 0), 120),
    ("patas_frente",  (-2, -20, 175), (0, -1, 0), 120),
    ("patas_lado",    (-2, -10, 175), (-1, 0, 0), 120),
    ("base_abajo",    (-2, 14, 0),    (0, 0, -1), 220),
    ("completo_lado", (-2, 14, 150),  (-1, 0, 0), 320),
]
for nombre, c, d, w in vistas:
    c = Vector(c); cam.data.ortho_scale = w
    cam.location = c + Vector(d) * 1500
    up = 'Y' if d[2] == 0 else 'Y'
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y' if d[2] == 0 else 'X').to_euler()
    sc.render.filepath = f"{out}/{nombre}.png"
    bpy.ops.render.render(write_still=True)
    print("VISTA", nombre, tuple(c), w)
