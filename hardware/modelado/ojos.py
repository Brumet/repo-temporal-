"""
Ojos del cuervo como insertos de resina transparente.

Cada inserto:
  - Por fuera conserva la superficie esculpida del ojo (iris y globo): al imprimirlo en
    resina transparente, donde hay más material se ve más oscuro y donde hay menos, más
    claro (efecto litofanía).
  - Atraviesa la pared de la cabeza por un agujero ajustado y se apoya con un reborde por
    dentro: se mete desde el interior de la cabeza y no puede salirse hacia afuera.
  - Detrás lleva un alojamiento donde el módulo LED entra justo, con una ranura para los cables.

La cabeza recibe el agujero, el escalón para el reborde y un túnel hacia el interior.

Uso: python ojos.py cuervo_reparado.stl carpeta_salida
Todas las medidas en mm. Cambiar LED_D / LED_T cuando se midan los módulos reales.
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

# ——— Medidas (ajustables) ———
LED_D = 8.9       # diámetro del PCB redondo del módulo WS2812B (medido)
LED_T = 2.6       # grosor total PCB + LED 5050 (medido)
R_TAPON = 2.8     # radio del tapón que atraviesa la pared (cubre el globo ocular)
PROF = 3.5        # del ápice del ojo al fondo del tapón: grosor máximo de la "litofanía"
R_REBORDE = 4.4   # reborde que se apoya por dentro
T_REBORDE = 1.0
LED_CUERPO = 5.1  # rebaje para el LED 5050 (4,8 × 4,9 medido + holgura)
LED_CUERPO_T = 1.2  # profundidad del rebaje (el LED sobresale ~1,6 del PCB)
PARED_CUNA = 1.0  # (sin uso: el LED queda en un bolsillo de la cabeza)
HOLG_AJUSTE = 0.10  # holgura radial del tapón y reborde en su agujero (ajuste firme en resina)
HOLG_LED = 0.20     # holgura radial del LED en su cuna
FONDO_ESC = 1.5     # el escalón pasa 1,5 mm detrás de la cuna (espacio para soldaduras)
R_CANAL = 2.0       # canal de cables Ø 4 mm desde detrás de cada LED hacia el centro de la cabeza
CENTRO_CABEZA = [1.5, -48.0, 266.0]   # dentro del macizo de la cabeza (se une al hueco interior después)
RANURA = 4.0        # ancho de la ranura para los 3 cables
SEG = 96

# Ojos medidos sobre la malla (ápice del iris y eje hacia afuera), ver docs/08-diseno-interno.md
OJOS = {
    "izq": {"apice": [-17.07, -55.80, 263.99], "eje": [-0.561, -0.806, -0.188]},
    "der": {"apice": [18.72, -68.26, 267.05], "eje": [0.906, 0.060, -0.420]},
}

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
t = trimesh.load_mesh(src, process=True)   # STL sin índice: hay que unir vértices
cuervo = mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
assert cuervo.status() == mf.Error.NoError, cuervo.status()


def marco(apice, eje):
    """Matriz 3x4 que lleva el eje Z local al eje del ojo con origen en el ápice."""
    z = np.asarray(eje, float); z /= np.linalg.norm(z)
    x = np.cross([0, 0, 1], z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.column_stack([x, y, z, np.asarray(apice, float)])


def cil(r, z0, z1, M):
    return mf.Manifold.cylinder(z1 - z0, r, r, SEG).translate([0, 0, z0]).transform(M)


def a_trimesh(man):
    me = man.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)


z_reb = -PROF - T_REBORDE                    # fondo del reborde
z_cuna = z_reb - (LED_T - LED_CUERPO_T)       # fondo del PCB del LED (el cuerpo entra en el rebaje)
r_cuna_i = LED_D / 2 + HOLG_LED
r_cuna_o = r_cuna_i + PARED_CUNA
r_esc = max(R_REBORDE, r_cuna_i) + HOLG_AJUSTE  # escalón en la cabeza: reborde + bolsillo del LED
informe = {"medidas": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}}
cabeza = cuervo
for nombre, o in OJOS.items():
    M = marco(o["apice"], o["eje"])
    tapon = cil(R_TAPON, -PROF, 6, M) ^ cuervo
    # El reborde y la cuna pueden ir desplazados del eje (hasta R_REBORDE - R_TAPON) si la pared es
    # delgada por un lado: se mide hacia dónde se rompe y se corre en sentido contrario.
    desp = np.zeros(2)
    for _ in range(6):
        Md = M.copy(); Md[:, 3] = M[:, 3] + M[:, :2] @ desp
        escalon = cil(r_esc, z_cuna - FONDO_ESC, -PROF, Md)
        fuera = escalon - cuervo
        if fuera.volume() < 0.5:
            break
        c = np.asarray(fuera.to_mesh().vert_properties)[:, :3].mean(0) - M[:, 3]
        dir2 = np.array([c @ M[:, 0], c @ M[:, 1]]); dir2 /= np.linalg.norm(dir2) + 1e-9
        desp = desp - 0.4 * dir2
        lim = R_REBORDE - R_TAPON - 0.2
        if np.linalg.norm(desp) > lim:
            desp = desp / np.linalg.norm(desp) * lim
    reborde = cil(R_REBORDE, z_reb, -PROF, Md)
    # Encastre del LED: rebaje cuadrado detrás del reborde donde entra el cuerpo del LED 5050
    rebaje = mf.Manifold.cube([LED_CUERPO, LED_CUERPO, LED_CUERPO_T + 0.01]).translate(
        [-LED_CUERPO / 2, -LED_CUERPO / 2, z_reb - 0.01]).transform(Md)
    inserto = tapon + reborde - rebaje
    p_atras = Md[:, :3] @ [0, 0, z_cuna - FONDO_ESC + 0.5] + Md[:, 3]
    canal = mf.Manifold.batch_hull([mf.Manifold.sphere(R_CANAL, 32).translate(list(p_atras)),
                                    mf.Manifold.sphere(R_CANAL, 32).translate(CENTRO_CABEZA)])
    hueco = cil(R_TAPON + HOLG_AJUSTE, -PROF, 8, M) + escalon + canal
    interno = escalon + canal
    asoma = interno.volume() - (interno ^ cuervo).volume()
    cabeza = cabeza - hueco
    a_trimesh(inserto).export(out / f"ojo_{nombre}.stl")
    # grosor de resina sobre el eje y en el borde del tapón (para el efecto de luz)
    informe[nombre] = {"volumen_inserto_mm3": round(inserto.volume(), 1),
                       "asoma_por_fuera_mm3": round(asoma, 2),
                       "led_a_superficie_mm": round(PROF + T_REBORDE - LED_CUERPO_T, 2), "led_desplazado_mm": round(float(np.linalg.norm(desp)), 2)}
    print(nombre, informe[nombre], flush=True)

a_trimesh(cabeza).export(out / "cuervo_con_ojos.stl")
(out / "ojos.json").write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
print("listo:", sorted(p.name for p in out.iterdir()))
