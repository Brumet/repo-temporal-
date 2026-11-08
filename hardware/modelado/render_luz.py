import bpy, sys, json
from mathutils import Vector, Matrix
d, color, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
col = {"rojo": (1, 0.04, 0.01, 1), "blanco": (1, 0.9, 0.8, 1), "azul": (0.05, 0.3, 1, 1)}[color]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 160; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 24; sc.cycles.transmission_bounces = 24; sc.cycles.glossy_bounces = 12
sc.render.resolution_x = sc.render.resolution_y = 640
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new("w"); sc.world = w; w.color = (0.015, 0.015, 0.015)
M = json.load(open(f"{d}/ojos.json"))["der"]["marco"]
c, e, x, y = (Vector(M[k]) for k in "cexy"); zl = M["zl"]
def mat(n, **kw):
    m = bpy.data.materials.new(n); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(b.outputs[0], o.inputs[0])
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m
vid = mat("vidrio", **{"Base Color": (1, 1, 1, 1), "Transmission Weight": 1.0, "Roughness": 0.04, "IOR": 1.52})
negro = mat("negro", **{"Base Color": (0.012, 0.012, 0.014, 1), "Roughness": 0.35})
blanco = mat("pcb", **{"Base Color": (0.8, 0.8, 0.8, 1), "Roughness": 0.6})
emi = bpy.data.materials.new("led"); emi.use_nodes = True; nt = emi.node_tree; nt.nodes.clear(); nt.nodes.new("ShaderNodeOutputMaterial")
em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = col; em.inputs[1].default_value = 40
nt.links.new(em.outputs[0], [n for n in nt.nodes if n.bl_idname=="ShaderNodeOutputMaterial"][0].inputs[0])
for f, m in (("ojo_der.stl", vid), ("cabeza_ojos.stl", negro)):
    bpy.ops.wm.stl_import(filepath=f"{d}/{f}"); o = bpy.context.selected_objects[0]; o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
R = Matrix((x, y, e)).transposed().to_4x4()
def poner(o, z):
    o.matrix_world = Matrix.Translation(c + e * z) @ R
bpy.ops.mesh.primitive_cube_add(size=1); cu = bpy.context.object; cu.scale = (5, 5, 1.5); cu.data.materials.append(blanco); poner(cu, zl - 1.4)
bpy.ops.mesh.primitive_circle_add(radius=1.75, fill_type='NGON', vertices=48); di = bpy.context.object; di.data.materials.append(emi); poner(di, zl - 0.62)
bpy.ops.mesh.primitive_cylinder_add(radius=4.4, depth=0.3); pc = bpy.context.object; pc.data.materials.append(negro); poner(pc, zl - 2.4)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 16; cam.data.clip_end = 1000
cam.matrix_world = Matrix.Translation(c + e * 60) @ R
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
