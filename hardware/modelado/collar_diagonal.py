"""
Collar v5 (pedido de Bru): cortar cada cuerda donde YA cuelga libre (justo debajo de donde toca la pluma), con un corte
DIAGONAL (bisel) limpio para resanar, + agujero para pasador Ø1 mm en las dos caras (alinea y refuerza el pegado).
El collar = dije + cuerdas libres por debajo de los cortes. El cuerpo queda con el resto de la cuerda.
Uso: python collar_diagonal.py cuervo_reparado.stl cuerpo.stl hebras.npz salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

sol_f, cue_f, hb_f, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
Z_CORTE = {"izq": 209.0, "der": 209.0}     # cuelgan libres por debajo de ~z 210 (secciones medidas)
ANG, PIN_D, PIN_L, HOLG = np.radians(40), 1.0, 3.0, 0.08
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
SOL = man(trimesh.load_mesh(sol_f, process=True)); CUE = man(trimesh.load_mesh(cue_f, process=True)); H = np.load(hb_f)


def marco(z_axis):
    z = z_axis / np.linalg.norm(z_axis); x = np.cross([0, 0, 1.0], z)
    if np.linalg.norm(x) < 1e-6: x = np.array([1.0, 0, 0])
    x /= np.linalg.norm(x); y = np.cross(z, x); return x, y, z


cortes, pines, info = [], [], {}
for k in ("izq", "der"):
    p = H[k + "_eje"]; i = int(np.argmin(abs(p[:, 2] - Z_CORTE[k])))
    c = p[i]; T = p[min(i + 4, len(p) - 1)] - p[max(i - 4, 0)]; T /= np.linalg.norm(T)      # T apunta hacia arriba
    atras = np.array([0, 1.0, 0]) - T * T[1]; atras /= np.linalg.norm(atras)              # hacia el cuerpo
    nrm = np.cos(ANG) * T + np.sin(ANG) * atras                                           # normal del plano (lado de arriba)
    x, y, z = marco(nrm)
    arriba = mf.Manifold.cube([16, 16, 12]).translate([-8, -8, 0]).transform(np.column_stack([x, y, z, c]))
    bola = mf.Manifold.sphere(4.5, 64).translate(list(c))
    cortes.append(arriba ^ bola)
    xp, yp, zp = marco(T)
    pines.append(mf.Manifold.cylinder(2 * PIN_L, (PIN_D + HOLG) / 2, (PIN_D + HOLG) / 2, 32).translate([0, 0, -PIN_L]).transform(np.column_stack([xp, yp, zp, c])))
    info[k] = {"punto": np.round(c, 2).tolist(), "eje": np.round(T, 3).tolist(), "angulo_bisel": 40}
A = SOL - cortes[0] - cortes[1]
partes = sorted(A.decompose(), key=lambda q: -q.volume())
cand = [q for q in partes[1:] if q.volume() > 300]
collar = max(cand, key=lambda q: q.volume())
print("piezas tras cortar:", [round(q.volume(), 1) for q in partes[:5]], "| collar", round(collar.volume(), 1))
bb = tm(collar).bounds; print("collar z", bb[:, 2].round(1))
cuerpo = CUE - collar
for pn in pines: collar = collar - pn; cuerpo = cuerpo - pn
cp = sorted(collar.decompose(), key=lambda q: -q.volume()); bp = sorted(cuerpo.decompose(), key=lambda q: -q.volume())
print("collar piezas", [round(q.volume(), 1) for q in cp[:3]], "| cuerpo piezas", [round(q.volume(), 1) for q in bp[:3]])
tm(cp[0]).export(out / "collar.stl"); tm(bp[0]).export(out / "cuerpo_sin_collar.stl")
info["collar_mm3"] = round(cp[0].volume(), 1); json.dump(info, open(out / "collar.json", "w"), indent=1)
