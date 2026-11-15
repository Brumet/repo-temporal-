"""Genera en Blender (sin ventana) los textos del grabado de la tapa como STL (plano XY, centrados, 1 mm de alto).
Uso: blender -b --python texto_tapa.py -- carpeta_salida"""
import bpy, sys
out = sys.argv[-1]
LINEAS = {"brumet": ("BRUMET", 9.0), "serie": ("CUERVO  ·  SERIE CERO", 4.2)}
for n in range(1, 5): LINEAS[f"num{n}"] = (f"Nº {n:02d} / 04", 4.2)
for nombre, (txt, tam) in LINEAS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.object.text_add(location=(0, 0, 0)); t = bpy.context.object
    t.data.body = txt; t.data.size = tam; t.data.extrude = 0.5; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
    if nombre == "brumet": t.data.space_character = 1.25
    bpy.ops.object.convert(target='MESH'); t.location = (0, 0, 0.5)
    bpy.ops.object.transform_apply(location=True)
    bpy.ops.wm.stl_export(filepath=f"{out}/texto_{nombre}.stl", export_selected_objects=True)
