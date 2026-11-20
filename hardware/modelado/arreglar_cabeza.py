"""Quita a la cabeza lo que choca con el labio del cuello (+0,15 mm de holgura para pegamento) y limpia trozos sueltos.
Uso: python arreglar_cabeza.py cabeza_ojos.stl superior.stl salida.stl"""
import sys
import numpy as np, trimesh, manifold3d as mf
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
cab_f, sup_f, out = sys.argv[1:4]
C = man(trimesh.load_mesh(cab_f, process=True)); S = man(trimesh.load_mesh(sup_f, process=True))
S = S ^ mf.Manifold.cube([200, 200, 70]).translate([-100, -100, 225])          # solo el cuello
H = 0.15
for d in [(0, 0, 0)] + [tuple(v) for v in (np.vstack([np.eye(3), -np.eye(3), (np.array([[1, 1, 0], [1, -1, 0], [-1, 1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1]]) / np.sqrt(2))]) * H)]:
    C = C - S.translate(list(d))
P = sorted(C.decompose(), key=lambda q: -q.volume())
print("cabeza piezas", [round(q.volume(), 2) for q in P[:3]], "| choque restante", round((P[0] ^ S).volume(), 3))
tm(P[0]).export(out)
