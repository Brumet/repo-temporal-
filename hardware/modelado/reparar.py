"""
Deja la malla del cuervo cerrada y sin defectos para poder hacer cortes y uniones exactas.
Quita las basuritas sueltas, repara aristas defectuosas y cierra agujeros (MeshFix),
y comprueba que manifold3d la acepte.

Uso: python reparar.py "forma preliminar.stl" cuervo_reparado.stl
"""
import sys, time
import numpy as np, trimesh, pymeshfix, manifold3d as mf

src, dst = sys.argv[1], sys.argv[2]
t = time.time()
m = trimesh.load_mesh(src, process=True)
partes = m.split(only_watertight=False)
m = max(partes, key=lambda p: len(p.faces))
print(f"pieza principal: {len(m.faces):,} caras (se descartan {len(partes) - 1} sueltas)", flush=True)
fx = pymeshfix.MeshFix(np.asarray(m.vertices, float), np.asarray(m.faces, np.int32))
fx.repair(joincomp=True, remove_smallest_components=False)
r = trimesh.Trimesh(fx.points, fx.faces, process=True)
print(f"reparada: {len(r.faces):,} caras · estanca={r.is_watertight} · volumen={r.volume/1000:.1f} cm³ · {time.time()-t:.0f} s", flush=True)
M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(r.vertices, np.float32), tri_verts=np.asarray(r.faces, np.uint32)))
print("manifold3d:", M.status(), "· volumen", round(M.volume() / 1000, 1), "cm³")
r.export(dst)
print("guardada", dst)
