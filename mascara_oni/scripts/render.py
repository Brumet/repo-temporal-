"""Renderiza una malla de la máscara desde varias vistas y monta una hoja de contacto.
Uso: python render.py export/mascara_v1.ply renders/v1 [muestras]
"""
import sys, os, math
import bpy
import numpy as np
import imageio.v3 as iio

src, outbase = sys.argv[1], sys.argv[2]
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 48
os.makedirs(os.path.dirname(outbase), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.wm.ply_import(filepath=os.path.abspath(src))
ob = bpy.context.selected_objects[0]
bpy.ops.object.shade_smooth()

# material: hueso / laca blanca, con suciedad en cavidades (AO)
mat = bpy.data.materials.new("hueso"); mat.use_nodes = True
nt = mat.node_tree; b = nt.nodes["Principled BSDF"]
ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 6
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.30, 0.26, 0.21, 1)
ramp.color_ramp.elements[1].color = (0.86, 0.84, 0.78, 1)
nt.links.new(ao.outputs["AO"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.55
b.inputs["Subsurface Weight"].default_value = 0.08
ob.data.materials.append(mat)

w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.33, 0.22, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

def area(loc, energy, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object; l.data.energy = energy; l.data.size = size
    l.constraints.new('TRACK_TO').target = tgt
    return l

tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt)
tgt.location = (0, -40, 70)
area((-250, -350, 350), 9e6, 250)    # luz principal arriba-izquierda
area((300, -200, 0), 2.5e6, 300)     # relleno
area((0, 300, 300), 4e6, 200)        # contraluz

bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam
cam.constraints.new('TRACK_TO').target = tgt
cam.data.lens = 85; cam.data.clip_end = 5000

sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.resolution_x = 800; sc.render.resolution_y = 1000
sc.view_settings.view_transform = 'AgX'

vistas = {
    "frente": (0, -1, 0.05),
    "tres_cuartos": (-0.65, -0.75, 0.22),   # como la referencia: girada, vista algo desde arriba
    "lado": (-1, -0.02, 0.05),
    "tres_cuartos_der": (0.7, -0.7, 0.1),
}
paths = []
for name, d in vistas.items():
    d = np.array(d) / np.linalg.norm(d)
    cam.location = tuple(np.array(tgt.location) + d * 1250)
    sc.render.filepath = os.path.abspath(f"{outbase}_{name}.png")
    bpy.ops.render.render(write_still=True)
    paths.append(sc.render.filepath)

imgs = [iio.imread(p)[..., :3] for p in paths]
sheet = np.concatenate(imgs, axis=1)
iio.imwrite(os.path.abspath(f"{outbase}_hoja.jpg"), sheet, quality=88)
print("hoja:", f"{outbase}_hoja.jpg")
