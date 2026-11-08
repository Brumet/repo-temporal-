"""
Paso 1 de los ojos: deja el ojo izquierdo liso y redondo como el derecho.

El ojo derecho esculpido es una esfera lisa (r = 6,78 mm, globo_esfera.py). Se pone una esfera
igual (espejada) detrás de los párpados del ojo izquierdo y se une a la cabeza: tapa el iris
tallado y los párpados la recortan solos, como un ojo real. Solo se conserva la parte de la
esfera que queda dentro de la cuenca (no asoma por la nuca ni por dentro del hueco).

Uso: python alisar_ojos.py cabeza.stl cuervo_reparado.stl globos.json espejo.json salida.stl [dx dy dz]
"""
import sys, json
import numpy as np, trimesh, manifold3d as mf

cab_f, sol_f, gl_f, esp_f, out = sys.argv[1:6]
extra = np.array([float(v) for v in sys.argv[6:9]]) if len(sys.argv) > 8 else np.zeros(3)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
G = json.load(open(gl_f))["der"]; E = json.load(open(esp_f))
c = np.array(G["centro_esfera"]); r = G["radio"]
cl = c.copy(); cl[0] = 2 * E["X0"] - cl[0]; cl += np.array(E["traslacion"]) + extra
esf = mf.Manifold.sphere(r, 256).translate(list(cl))
# Limitar la esfera a la cuenca: cilindro corto a lo largo del eje del ojo izquierdo
e = np.array(G["eje"]); e[0] = -e[0]; e /= np.linalg.norm(e)
x = np.cross([0, 0, 1], e); x /= np.linalg.norm(x); y = np.cross(e, x)
apice = cl + e * r
M = np.column_stack([x, y, e, apice])
cuenca = mf.Manifold.cylinder(4.5, 5.5, 5.5, 128).translate([0, 0, -4.0]).transform(M)
parche = esf ^ cuenca
CAB = man(trimesh.load_mesh(cab_f, process=True))
res = CAB + parche
partes = res.decompose()
print("centro", cl.round(2), "ápice", apice.round(2), "volumen agregado mm³", round(res.volume() - CAB.volume(), 1), "piezas", len(partes))
tm(res).export(out)


# ——— Ojo derecho: dentro del contorno de su globo, superficie = esfera perfecta ———
if len(sys.argv) > 9:
    g = trimesh.load_mesh(sys.argv[9], process=True)
    cR = np.array(G["centro_esfera"]); eR = np.array(G["eje"]); eR /= np.linalg.norm(eR)
    xR = np.cross([0, 0, 1], eR); xR /= np.linalg.norm(xR); yR = np.cross(eR, xR)
    ar = g.area_faces; c0 = ar @ g.triangles_center / ar.sum()
    bordes = trimesh.grouping.group_rows(g.edges_sorted, require_count=1)
    P = g.vertices[np.unique(g.edges_sorted[bordes])] - c0
    th = np.arctan2(P @ yR, P @ xR); rr = np.hypot(P @ xR, P @ yR)
    ts = np.linspace(-np.pi, np.pi, 120, endpoint=False)
    R = np.array([np.median(rr[np.abs((th - t + np.pi) % (2 * np.pi) - np.pi) < 0.1]) for t in ts]) + 0.1
    sec = mf.CrossSection([[(float(rv * np.cos(t)), float(rv * np.sin(t))) for t, rv in zip(ts, R)]])
    MR = np.column_stack([xR, yR, eR, c0 - eR * 3.0])
    prisma = mf.Manifold.extrude(sec, 8.0).transform(MR)
    esfR = mf.Manifold.sphere(G["radio"] + 0.28, 384).translate(list(cR))   # 0,28 mm sobre el globo: lo cubre entero
    antes = res.volume()
    res = res + (prisma ^ esfR)   # solo agrega: rellena hasta la esfera sin dejar escalón con el párpado
    print("derecho: cambio de volumen mm³", round(res.volume() - antes, 2))
    tm(max(res.decompose(), key=lambda q: q.volume())).export(out)
