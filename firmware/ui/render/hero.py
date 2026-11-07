import bpy, sys, math
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
S,mode,W,H,samples=args[0],args[1],int(args[2]),int(args[3]),int(args[4])
camdir=Vector(tuple(map(float,args[5].split(",")))) if len(args)>5 else Vector((-0.55,-0.83,0.06))
dist=float(args[6]) if len(args)>6 else 470
tgt=Vector(tuple(map(float,args[7].split(",")))) if len(args)>7 else Vector((5.7,-32,236))
sc=bpy.context.scene
ob=bpy.data.objects["CUERVO 300MM"]
for o in list(bpy.data.objects):
    if o!=ob: bpy.data.objects.remove(o)
dg=bpy.context.evaluated_depsgraph_get()
eyes=[]
for sx in (-1,1):
    ok,loc,nor,idx,o,m=sc.ray_cast(dg,Vector((sx*200,-64,268.0)),Vector((-sx,0,0)))
    eyes.append((loc,nor)); print("EYE",sx,tuple(round(v,2) for v in loc),tuple(round(v,2) for v in nor))
# material
def newmat(n):
    m=bpy.data.materials.new(n)
    try: m.use_nodes=True
    except Exception: pass
    nt=m.node_tree
    for x in list(nt.nodes): nt.nodes.remove(x)
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    return m,nt,out
mat,nt0,out0=newmat("raven")
b=nt0.nodes.new("ShaderNodeBsdfPrincipled"); nt0.links.new(b.outputs[0],out0.inputs[0])
b.inputs["Base Color"].default_value=(0.012,0.011,0.014,1)
b.inputs["Roughness"].default_value=0.36
b.inputs["Coat Weight"].default_value=0.25
b.inputs["Coat Roughness"].default_value=0.2
ob.data.materials.clear(); ob.data.materials.append(mat)
sc.render.engine='CYCLES'; sc.cycles.samples=samples; sc.cycles.use_denoising=True
try: sc.cycles.device='GPU'
except: pass
sc.render.resolution_x=W; sc.render.resolution_y=H; sc.render.resolution_percentage=100
sc.view_settings.view_transform='Standard'; sc.view_settings.look='None'
sc.render.film_transparent=(mode=="base")
w=bpy.data.worlds.new("w"); sc.world=w
try: w.use_nodes=True
except Exception: pass
w.color=(0,0,0)
if w.node_tree:
    for x in w.node_tree.nodes:
        if x.type=="BACKGROUND": x.inputs[1].default_value=0
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.lens=100; cam.data.clip_start=1; cam.data.clip_end=10000; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=36
cam.location=tgt+camdir.normalized()*dist
cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
def light(name,kind,loc,energy,color,size=None,target=None):
    l=bpy.data.lights.new(name,kind); l.energy=energy; l.color=color
    if size is not None:
        if kind=='AREA': l.size=size
        else: l.shadow_soft_size=size
    o=bpy.data.objects.new(name,l); sc.collection.objects.link(o); o.location=loc
    if target is not None: o.rotation_euler=(target-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    return o
head=Vector((5.7,-50,262))
full=len(args)>8 and args[8]=="full"
if mode=="base" and full:
    mid=Vector((5.7,-10,170))
    light("key",'AREA',mid+Vector((-220,-760,520)),8.5e6,(1,.97,.94),520,mid)
    light("top",'AREA',head+Vector((60,40,420)),1.2e6,(.9,.9,1),300,head)
    light("rimL",'AREA',mid+Vector((-620,520,260)),5e6,(.62,.66,1),420,mid)
    light("rimR",'AREA',mid+Vector((640,460,160)),4e6,(.78,.68,1),420,mid)
    light("fill",'AREA',mid+Vector((-560,-560,-60)),5e5,(.8,.85,1),600,mid)
    sc.render.filepath=f"{S}/hero_base.png"
elif mode=="base":
    light("key",'AREA',head+Vector((-120,-420,300)),2.6e6,(1,.97,.94),260,head)
    light("top",'AREA',head+Vector((60,40,420)),1.2e6,(.9,.9,1),300,head)
    light("rimL",'AREA',head+Vector((-320,260,120)),1.4e6,(.62,.66,1),220,head)
    light("rimR",'AREA',head+Vector((340,220,60)),1.1e6,(.78,.68,1),220,head)
    light("fill",'AREA',head+Vector((-300,-300,-80)),1.2e5,(.8,.85,1),400,head)
    sc.render.filepath=f"{S}/hero_base.png"
else:
    em,nt,out=newmat("eye")
    e=nt.nodes.new("ShaderNodeEmission"); e.inputs[1].default_value=90
    nt.links.new(e.outputs[0],out.inputs[0])
    for loc,nor in eyes:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=3.2,location=loc-nor*0.6)
        s=bpy.context.object; s.data.materials.append(em)
        light("eyeL",'POINT',loc+nor*3.5,3.5e3,(1,1,1),2.0)
    sc.render.filepath=f"{S}/hero_light.png"
sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA' if mode=="base" else 'RGB'
bpy.ops.render.render(write_still=True)
