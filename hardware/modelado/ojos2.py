"""
Ojos v2 sobre la cabeza ya separada (hueca).

Inserto de resina transparente por ojo:
  - Por FUERA: casquete liso (esfera que pasa por el ápice del ojo y por el borde del párpado).
  - Por DENTRO: el relieve del iris esculpido, copiado hacia adentro T_BASE mm. El grosor varía
    con el relieve: los surcos del iris quedan más gruesos (más oscuros con la luz detrás).
  - Collar de unión + reborde que se apoya en un asiento: se mete desde el interior de la cabeza.
Cabeza: agujero ajustado, un refuerzo cilíndrico por dentro (recortado a la forma de la cabeza)
con el asiento del reborde y el bolsillo del LED (PCB Ø 8,9 × 2,6 mm medido), abierto hacia el
interior para los cables.

Uso: python ojos2.py cabeza.stl cuervo_reparado.stl salida_dir
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

R_TAPON = 2.8; HOLG = 0.10
T_BASE = 1.4          # grosor mínimo del relieve interior
R_REB = 4.4; T_REB = 1.0; PARED_TUBO = 0.6
Z_REB = -4.3          # cara exterior del reborde (desde el ápice, hacia adentro negativo)
LED_D, LED_T, HOLG_LED = 8.9, 2.6, 0.2
R_BOSS, Z_BOSS = 6.6, -11.0
SEG = 96
OJOS = {"izq": ([-17.07, -55.80, 263.99], [-0.561, -0.806, -0.188]),
        "der": ([18.72, -68.26, 267.05], [0.906, 0.060, -0.420])}

cab_f, sol_f, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
CAB = man(trimesh.load_mesh(cab_f, process=True))
sol_t = trimesh.load_mesh(sol_f, process=True); SOL = man(sol_t)
print("cargado", CAB.status(), SOL.status(), flush=True)


def marco(a, e):
    z = np.asarray(e, float); z /= np.linalg.norm(z)
    x = np.cross([0, 0, 1], z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.column_stack([x, y, z, np.asarray(a, float)])


def cil(r, z0, z1, M):
    return mf.Manifold.cylinder(z1 - z0, r, r, SEG).translate([0, 0, z0]).transform(M)


info = {}
cabeza = CAB
for nom, (a, e) in OJOS.items():
    M = marco(a, e); a = np.asarray(a); z = M[:, 2]
    # borde del párpado: altura media de la superficie a radio R_TAPON
    loc = []
    for t in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        o = a + M[:, 0] * R_TAPON * np.cos(t) + M[:, 1] * R_TAPON * np.sin(t) + z * 6
        h = sol_t.ray.intersects_location([o], [-z], multiple_hits=False)[0]
        if len(h): loc.append((h[0] - a) @ z)
    zr = float(np.median(loc))
    c = (R_TAPON ** 2 + zr ** 2) / (2 * zr)        # centro de la esfera sobre el eje (negativo)
    Rs = -c
    domo = mf.Manifold.sphere(Rs, 192).translate([0, 0, c]).transform(M)
    tapon = cil(R_TAPON, Z_REB, 1.0, M) ^ domo                      # sólido bajo el casquete liso
    relieve_sombra = (SOL ^ cil(R_TAPON + 1, -8, 6, M)).translate(list(-z * T_BASE))
    capa = tapon - relieve_sombra                                    # entre el iris copiado y el casquete
    tubo = cil(R_TAPON, Z_REB, -T_BASE - 0.2, M) - cil(R_TAPON - PARED_TUBO, Z_REB - 1, 0, M)
    reborde = cil(R_REB, Z_REB - T_REB, Z_REB, M) - cil(R_TAPON - PARED_TUBO, Z_REB - 2, Z_REB + 1, M)
    inserto = capa + tubo + reborde
    piezas = inserto.decompose(); inserto = max(piezas, key=lambda p: p.volume())
    # Cabeza: refuerzo interior recortado a la forma, agujero, asiento del reborde y bolsillo del LED
    boss = cil(R_BOSS, Z_BOSS, -1.0, M) ^ SOL
    z_led0 = Z_REB - T_REB
    hueco = (cil(R_TAPON + HOLG, Z_REB - 0.01, 8, M) + cil(R_REB + HOLG, z_led0 - 0.01, Z_REB + 0.01, M)
             + cil(LED_D / 2 + HOLG_LED, Z_BOSS - 1, z_led0, M))
    cabeza = (cabeza + boss) - hueco
    tm(inserto).export(out / f"ojo_{nom}.stl")
    grosor = []
    for r in np.linspace(0, R_TAPON - 0.4, 8):
        for t in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            o = a + M[:, 0] * r * np.cos(t) + M[:, 1] * r * np.sin(t) + z * 6
            hs = tm(capa).ray.intersects_location([o], [-z], multiple_hits=True)[0]
            if len(hs) >= 2:
                dz = (hs - a) @ z; grosor.append(dz.max() - dz.min())
    info[nom] = {"radio_casquete_mm": round(Rs, 2), "borde_parpado_mm": round(zr, 2),
                 "grosor_min_mm": round(min(grosor), 2), "grosor_max_mm": round(max(grosor), 2),
                 "volumen_inserto_mm3": round(inserto.volume(), 1), "piezas_descartadas": len(piezas) - 1}
    print(nom, info[nom], flush=True)
tm(cabeza).export(out / "cabeza_ojos.stl")
info["cabeza_piezas"] = len(cabeza.decompose())
(out / "ojos.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print("listo", info["cabeza_piezas"])
