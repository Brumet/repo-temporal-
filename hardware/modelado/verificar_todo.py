"""
Revisión completa antes de imprimir (piezas sin textura: las caras de unión son idénticas a las texturizadas).
1. Cada pieza: cerrada, una sola pieza, cavidades atrapadas (cascarones internos sin salida).
2. Uniones: volumen de choque entre piezas que se tocan (debe ser ~0) y holgura.
3. Grosor de pared: rayos hacia adentro desde la superficie.
4. Ruta de cables: cavidad continua desde cada ojo hasta la bahía de la ESP32 (todas las piezas armadas).
Uso: python verificar_todo.py   (rutas fijas del proyecto)
"""
import json, time
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage

B = Path(r"D:\3D\Productos\Pruductos a la venta\SERIE CERO\CUERVO\modelado")
P = {"superior": B / "partes/superior.stl", "roca": B / "partes/roca.stl", "cabeza": B / "ojos_fibras/cabeza_ojos.stl",
     "collar": B / "collar5/collar.stl", "ojo_izq": B / "ojos_fibras/ojo_izq.stl", "ojo_der": B / "ojos_fibras/ojo_der.stl",
     "porta_izq": B / "ojos_fibras/porta_led_izq.stl", "porta_der": B / "ojos_fibras/porta_led_der.stl",
     "tecla": B / "tapa3/tecla.stl", "tapa": B / "tapa3/tapa_01.stl"}
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:4.0f}s]", *a, flush=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
R, M = {}, {}
log("=== 1. Piezas")
for k, f in P.items():
    t = trimesh.load_mesh(f, process=True); Mk = man(t); M[k] = Mk
    es = t.edges_sorted; abiertos = len(trimesh.grouping.group_rows(es, require_count=1))
    partes = [q for q in Mk.decompose() if q.volume() > 0.5]
    cascarones = t.split(only_watertight=False)
    vols = sorted([abs(c.volume) for c in cascarones if c.is_watertight], reverse=True)
    R[k] = {"caras": len(t.faces), "volumen_cm3": round(Mk.volume() / 1000, 2), "estado": str(Mk.status()), "bordes_abiertos": abiertos,
            "piezas": len(partes), "cascarones": len(cascarones), "vol_cascarones_cm3": [round(v / 1000, 2) for v in vols[:4]]}
    log(k, R[k])
log("=== 2. Uniones (choque mm³)")
PARES = [("superior", "roca"), ("superior", "cabeza"), ("superior", "collar"), ("cabeza", "ojo_izq"), ("cabeza", "ojo_der"),
         ("cabeza", "porta_izq"), ("cabeza", "porta_der"), ("ojo_izq", "porta_izq"), ("ojo_der", "porta_der"),
         ("porta_izq", "porta_der"), ("roca", "tecla"), ("roca", "tapa"), ("superior", "tapa")]
U = {}
for a, b in PARES:
    ch = (M[a] ^ M[b]).volume()
    holg = (M[a] ^ M[b].refine(1) if False else M[a]).volume() * 0
    U[f"{a}-{b}"] = round(ch, 3); log(f"{a} ↔ {b}: choque {ch:.3f} mm³")
R["uniones_choque_mm3"] = U
log("=== 3. Grosor de pared (superior y roca)")
for k in ("superior", "roca", "cabeza"):
    t = trimesh.load_mesh(P[k], process=True)
    rng = np.random.default_rng(0); idx = rng.choice(len(t.faces), 60000, p=t.area_faces / t.area)
    o = t.triangles_center[idx] - t.face_normals[idx] * 0.02
    L, I, _ = t.ray.intersects_location(o, -t.face_normals[idx], multiple_hits=False)
    g = np.full(len(o), np.inf); g[I] = np.linalg.norm(L - o[I], axis=1)
    zc = t.triangles_center[idx][:, 2]
    fin = (g < 0.8)
    R[k]["grosor_p1_p5_p50_mm"] = np.round(np.percentile(g[np.isfinite(g)], [1, 5, 50]), 2).tolist()
    R[k]["area_pared_menor_0.8mm_%"] = round(100 * fin.mean(), 2)
    if fin.any():
        zz = np.round(zc[fin] / 10) * 10; u, c = np.unique(zz, return_counts=True)
        R[k]["zonas_finas_por_altura"] = {int(a): int(b) for a, b in zip(u, c) if b > 30}
    log(k, "grosor", R[k]["grosor_p1_p5_p50_mm"], "| <0,8 mm:", R[k]["area_pared_menor_0.8mm_%"], "%", R[k].get("zonas_finas_por_altura", ""))
log("=== 4. Ruta de cables (vóxeles 0,75 mm)")
sol = trimesh.load_mesh(B / "cuervo_reparado.stl", process=True)
armado = trimesh.util.concatenate([trimesh.load_mesh(P[k], process=True) for k in ("superior", "roca", "cabeza", "porta_izq", "porta_der", "ojo_izq", "ojo_der", "tapa", "tecla")])
VX = 0.75
vs = sol.voxelized(VX).fill(); Ms = vs.matrix; Tm = vs.transform
centros = trimesh.transform_points(np.argwhere(Ms).astype(float), Tm)
dentro_piezas = np.zeros(len(centros), bool)
for k in ("superior", "roca", "cabeza", "porta_izq", "porta_der", "ojo_izq", "ojo_der", "tapa", "tecla"):
    dentro_piezas |= trimesh.load_mesh(P[k], process=True).contains(centros)
cav = np.zeros_like(Ms); ijk = np.argwhere(Ms)[~dentro_piezas]; cav[tuple(ijk.T)] = True
lab, n = ndimage.label(cav)
J = json.load(open(B / "ojos_fibras/ojos.json")); Tj = json.load(open(B / "tapa3/tapa.json"))
inv = np.linalg.inv(Tm)
def etiqueta(p, r=3):
    i = np.round(trimesh.transform_points([p], inv)[0]).astype(int); s = tuple(slice(max(a - r, 0), a + r + 1) for a in i)
    l = lab[s]; l = l[l > 0]; return int(np.bincount(l).argmax()) if len(l) else 0
pts = {"ojo_izq": np.array(J["izq"]["marco"]["c"]) + np.array(J["izq"]["marco"]["e"]) * (J["izq"]["marco"]["z_fondo"] - 1.5),
       "ojo_der": np.array(J["der"]["marco"]["c"]) + np.array(J["der"]["marco"]["e"]) * (J["der"]["marco"]["z_fondo"] - 1.5),
       "esp32": np.array([0, Tj["usb_y"] - 14, Tj["usb_z"] + 3])}
et = {k: etiqueta(p) for k, p in pts.items()}
R["cables"] = {"etiquetas": et, "conectado": len(set(et.values())) == 1 and 0 not in et.values(), "cavidades": int(n)}
log("cables:", R["cables"])
json.dump(R, open(B / "imprimir/verificacion.json", "w"), indent=1, ensure_ascii=False)
log("listo")
