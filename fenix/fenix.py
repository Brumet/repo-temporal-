"""
Llavero Fénix articulado (flexi), pensado para Bambu Lab A1 Combo (AMS lite).

Genera el modelo de forma paramétrica:
  - Alas articuladas (hombro + codo) y cola articulada, impresas ya montadas (print-in-place).
  - Cabeza, cuerpo, patas y garras FIJOS (una sola pieza rígida con la anilla).
  - Bisagras de eje vertical en forma de "C" con pivote de perfil trapezoidal (45°):
    sin soportes ni puentes, con tope de giro (±ANGULO) y retención vertical y lateral.
  - 4 colores: 1 rojo, 2 naranja, 3 amarillo, 4 negro (ojo).

Uso:  python3 fenix.py         -> escribe STL/3MF/PNG en ./salida
Requiere: numpy shapely manifold3d trimesh matplotlib
"""
import math
import os
import sys

import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, box
from shapely.ops import unary_union
import manifold3d as mf

# ---------------------------------------------------------------- parámetros
ESCALA = 0.9          # escala global del dibujo (las holguras NO se escalan)
G = 0.45              # holgura en el plano entre piezas móviles (mm)
C = 0.45              # holgura horizontal pivote/anillo (mm)
T = 4.0               # espesor estructural (rojo, bisagras)
H = {"rojo": 4.0, "naranja": 3.6, "amarillo": 3.2, "negro": 4.0, "relieve": 4.4}
PIN_R = 2.8           # radio máximo del pivote
PIN_BISEL = 1.0       # altura del bisel a 45° arriba y abajo del pivote
PARED = 1.5           # pared mínima del anillo en "C"
CUELLO = 2.2          # ancho del cuello que une el pivote a su pieza
ANGULO = 20.0         # giro permitido a cada lado (grados)
BASE_ECO = 2.0        # variante económica: color sólo por encima de esta altura
SEG = 72              # resolución de círculos

RI = PIN_R + C        # radio interior del anillo (a media altura)
RO = RI + PARED       # radio exterior del anillo

COLORES = ["rojo", "naranja", "amarillo", "negro"]
RGB = {"rojo": "#D7191C", "naranja": "#F46D0F", "amarillo": "#FFC814", "negro": "#151515"}
EXTRUSOR = {"rojo": 1, "naranja": 2, "amarillo": 3, "negro": 4}


# ---------------------------------------------------------------- utilidades 2D
def P(x, y):
    return np.array([x, y], float) * ESCALA


def circ(c, r):
    return Point(*c).buffer(r, SEG // 2)


def bezier(p0, p1, p2, n=24):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def trazo(pts, w0, w1):
    """Trazo afilado: unión de envolventes de círculos consecutivos."""
    pts = np.asarray(pts)
    rs = np.linspace(w0, w1, len(pts)) / 2
    partes = []
    for i in range(len(pts) - 1):
        a = circ(pts[i], rs[i])
        b = circ(pts[i + 1], rs[i + 1])
        partes.append(unary_union([a, b]).convex_hull)
    return unary_union(partes)


def pluma(raiz, ang, largo, ancho, curva=0.12, punta=1.25):
    """Pluma en forma de hoja curvada: raíz, ángulo (grados), largo, ancho máximo."""
    raiz = np.asarray(raiz, float)
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    n = np.array([-u[1], u[0]])
    L = largo * ESCALA
    p2 = raiz + u * L
    p1 = raiz + u * L * 0.5 + n * curva * L
    pts = bezier(raiz, p1, p2, 28)
    t = np.linspace(0, 1, len(pts))
    # perfil de hoja: ancho máximo hacia el 55 % y punta afilada (pero >= 'punta' mm)
    w = np.where(t < 0.5, 0.75 + 0.25 * t / 0.5, 1 - np.clip((t - 0.5) / 0.5, 0, 1) ** 0.8)
    w = np.maximum(punta, ancho * ESCALA * w)
    partes = [unary_union([circ(pts[i], w[i] / 2), circ(pts[i + 1], w[i + 1] / 2)]).convex_hull
              for i in range(len(pts) - 1)]
    return unary_union(partes)


def abanico(r0, r1, a0, a1, n, l0, l1, ancho, curva):
    """n plumas con raíz repartida entre r0 y r1, ángulos de a0 a a1 y largos de l0 a l1."""
    out = []
    for i, t in enumerate(np.linspace(0, 1, n)):
        out.append(pluma(r0 + (r1 - r0) * t, a0 + (a1 - a0) * t, l0 + (l1 - l0) * t, ancho, curva))
    return unary_union(out)


def espejo(g):
    return affinity.scale(g, -1, 1, origin=(0, 0))


def limpia(g):
    if g is None or g.is_empty:
        return Polygon()
    g = g.buffer(0)
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    return unary_union([x for x in getattr(g, "geoms", []) if isinstance(x, (Polygon, MultiPolygon))])


# ---------------------------------------------------------------- pieza
class Pieza:
    """Pieza rígida: capas de color 2D (en orden de dibujo) + sólidos 3D extra."""

    def __init__(self, nombre):
        self.nombre = nombre
        self.capas = []          # [(color, geom, altura)] en orden de dibujo
        self.pin3d = []          # sólidos manifold rojos (pivotes, anillos)
        self.quitar = []         # zonas 2D a excluir de las capas de color
        self.huella_extra = []   # huella 2D de los sólidos 3D (para holguras)

    def add(self, color, g, h=None):
        self.capas.append((color, g, H[color] if h is None else h))

    def contorno(self):
        g = unary_union([c[1] for c in self.capas] + self.huella_extra)
        for q in self.quitar:
            g = g.difference(q)
        return unary_union([g] + self.huella_extra)

    def recortar(self, g):
        self.quitar.append(g)

    def regiones(self):
        """Devuelve {(color, altura): geom} sin solapes (lo dibujado después tapa)."""
        out = []
        tapa = Polygon()
        quitar = unary_union(self.quitar) if self.quitar else Polygon()
        for color, g, h in reversed(self.capas):
            # 0.03 mm de solape entre colores vecinos para que se fusionen sin rendijas
            r = limpia(g.difference(tapa).buffer(0.03, 4).intersection(g.buffer(0.03, 4)).difference(quitar))
            tapa = unary_union([tapa, g])
            if not r.is_empty:
                out.append((color, r, h))
        return list(reversed(out))


# ---------------------------------------------------------------- bisagra
def perfil_pin(r_extra=0.0):
    """Perfil (r,z) del pivote: trapecio con biseles a 45° arriba y abajo."""
    r0 = PIN_R - PIN_BISEL + r_extra
    r1 = PIN_R + r_extra
    pts = [(0, -0.01), (r0, -0.01), (r1, PIN_BISEL), (r1, T - PIN_BISEL), (r0, T + 0.01), (0, T + 0.01)]
    if r_extra:  # holgura: alargar arriba/abajo para que corte limpio
        pts = [(0, -1), (r0 - 1, -1), (r0, 0), (r1, PIN_BISEL), (r1, T - PIN_BISEL), (r0, T), (r0 - 1, T + 1), (0, T + 1)]
    return pts


def solido_revolucion(perfil, centro):
    cs = mf.CrossSection([np.array(perfil, float)], mf.FillRule.EvenOdd)
    s = mf.Manifold.revolve(cs, SEG)
    return s.translate((centro[0], centro[1], 0))


def bisagra(A, B, centro, direccion):
    """A lleva el pivote + cuello (apunta hacia A, 'direccion'); B lleva el anillo en C.
    Se llama después de dibujar A y B, antes de calcular holguras entre ellas."""
    c = np.asarray(centro, float)
    d = np.asarray(direccion, float)
    d = d / np.linalg.norm(d)
    ang = math.degrees(math.atan2(d[1], d[0]))
    largo = RO + G + 2.0
    cuello = affinity.rotate(box(0, -CUELLO / 2, largo, CUELLO / 2), ang, origin=(0, 0))
    cuello = affinity.translate(cuello, *c)
    # barrido del cuello (con holgura) en todo el rango de giro -> abertura de la C
    barrido = unary_union([
        affinity.rotate(cuello.buffer(G, 8), a, origin=tuple(c))
        for a in np.linspace(-ANGULO, ANGULO, 21)
    ])
    disco_ro = circ(c, RO)
    anillo2d = disco_ro.difference(barrido)

    # --- A: despejar alrededor del anillo excepto el cuello; añadir cuello + pivote
    A.recortar(circ(c, RO + G).difference(cuello))
    A.add("rojo", cuello.intersection(circ(c, RO + G + 2.0)), T)
    A.pin3d.append(solido_revolucion(perfil_pin(), c))
    A.huella_extra.append(circ(c, PIN_R - PIN_BISEL - 0.15))

    # --- B: el resto de B no entra en el disco ni en el barrido; anillo 3D
    B.recortar(circ(c, RO - 0.8))
    B.recortar(barrido)
    anillo = extruir(anillo2d, T) - solido_revolucion(perfil_pin(C), c)
    B.pin3d.append(anillo)
    B.huella_extra.append(anillo2d)
    return dict(centro=c, dir=d, barrido=barrido, anillo2d=anillo2d)


# ---------------------------------------------------------------- 3D
def anillos_de(g):
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    out = []
    for p in polys:
        if p.is_empty or not isinstance(p, Polygon):
            continue
        out.append(np.array(p.exterior.coords[:-1]))
        out += [np.array(i.coords[:-1]) for i in p.interiors]
    return out


def extruir(g, h, z0=0.0):
    r = anillos_de(g)
    if not r:
        return mf.Manifold()
    cs = mf.CrossSection(r, mf.FillRule.EvenOdd)
    return mf.Manifold.extrude(cs, h - z0).translate((0, 0, z0))


# ---------------------------------------------------------------- diseño
def diseno():
    cuerpo, cola = Pieza("cuerpo"), Pieza("cola")
    hombro = {s: Pieza(f"brazo_{s}") for s in "DI"}
    mano = {s: Pieza(f"ala_{s}") for s in "DI"}

    # ---------- CUERPO (rígido: cuerpo + cuello + cabeza + anilla + patas + garras)
    torso = unary_union([
        circ(P(0, 3.0), 6.2).union(circ(P(0, -7.5), 3.6)).convex_hull,
        unary_union([circ(P(0, 3), 5.0), circ(P(1.0, 12.5), 3.8)]).convex_hull,
    ])
    cabeza = circ(P(1.6, 14.6), 4.4)
    # anilla reforzada: medidas absolutas (no escalan): agujero 3.2 mm, pared 2.0 mm
    anilla_ext = circ(P(-0.2, 22.3), 3.6)
    anilla_hueco = circ(P(-0.2, 22.3), 1.6)
    union_anilla = unary_union([circ(P(-0.2, 21.5), 3.2), circ(P(0.6, 16.5), 3.2)]).convex_hull
    # cresta (plumas hacia atrás/izquierda, como en la imagen)
    cresta_am = unary_union([
        pluma(P(-0.5, 17.0), 165, 10.5, 3.2, curva=-0.18, punta=1.8),
        pluma(P(-1.5, 15.0), 190, 9.5, 3.0, curva=-0.15, punta=1.8),
    ])
    cresta_na = unary_union([
        pluma(P(-0.5, 15.8), 178, 8.0, 3.0, curva=-0.15, punta=1.8),
        pluma(P(-1.0, 13.0), 205, 8.5, 3.0, curva=-0.12, punta=1.8),
        pluma(P(0.5, 10.0), 215, 6.5, 2.8, curva=-0.10, punta=1.8),
    ])
    cresta_ro = unary_union([
        pluma(P(0.0, 14.5), 185, 5.5, 3.0, curva=-0.12, punta=1.8),
        pluma(P(0.5, 12.0), 210, 5.0, 2.8, curva=-0.10, punta=1.8),
    ])
    pico = Polygon([P(4.4, 16.6), P(7.0, 16.6), P(9.4, 15.6), P(10.8, 13.6), P(10.6, 11.6),
                    P(9.6, 11.0), P(9.4, 12.6), P(8.0, 13.2), P(4.6, 12.4)]).buffer(0.35, 8)
    ojo = Point(*P(4.6, 15.4)).buffer(1.0, 16)
    ojo = affinity.scale(ojo, 1.35, 0.85)
    ceja = trazo(bezier(P(2.4, 17.3), P(4.6, 17.6), P(6.6, 16.4), 12), 1.2, 0.9)

    # patas fijas (muslo rojo, garras amarillas)
    def pata(s):
        m = trazo(bezier(P(3.8, -4.0), P(6.8, -6.0), P(7.6, -9.6), 14), 4.0, 3.0)
        pie = circ(P(8.4, -11.4), 1.9)
        dedos = unary_union([
            pluma(P(8.4, -11.4), -45, 4.0, 1.9, curva=-0.25, punta=1.5),
            pluma(P(8.4, -11.4), -80, 4.2, 1.9, curva=-0.25, punta=1.5),
            pluma(P(8.4, -11.4), -115, 3.8, 1.9, curva=-0.25, punta=1.5),
            pluma(P(8.6, -11.0), 10, 3.0, 1.8, curva=-0.30, punta=1.5),
        ])
        g = unary_union([pie, dedos])
        m, g = (m, g) if s > 0 else (espejo(m), espejo(g))
        return m, g

    pd, gd = pata(1)
    pi_, gi = pata(-1)

    cuerpo.add("rojo", unary_union([torso, cabeza, union_anilla, anilla_ext, pd, pi_]))
    cuerpo.add("amarillo", cresta_am, H["rojo"] - 0.4)  # cresta trasera
    cuerpo.add("naranja", cresta_na, H["rojo"] - 0.2)
    cuerpo.add("rojo", cresta_ro)
    cuerpo.add("rojo", unary_union([torso, cabeza]).difference(circ(P(-3.0, 13.5), 2.2)))
    cuerpo.add("amarillo", unary_union([gd, gi]), T)
    cuerpo.add("amarillo", pico, T)
    # relieve del pecho (plumas en V) y ceja
    v = []
    for i, y in enumerate([5.5, 2.0, -1.5, -5.0]):
        w = 4.2 - i * 0.6
        v.append(trazo(bezier(P(-w, y + 1.4), P(0, y - 1.6), P(w, y + 1.4), 16), 1.1, 1.1))
    cuerpo.add("rojo", unary_union(v), H["relieve"])
    cuerpo.add("rojo", ceja, H["relieve"])
    cuerpo.add("negro", ojo, H["negro"])
    cuerpo.recortar(anilla_hueco)

    # ---------- ALAS
    PS = P(11.2, 4.6)     # hombro
    PE = P(23.4, 10.2)    # codo
    for s in "DI":
        k = 1 if s == "D" else -1
        f = (lambda g: g) if k > 0 else espejo
        b, m = hombro[s], mano[s]
        # brazo (segmento interior): hueso + cobertoras y secundarias colgando
        hueso = trazo([PS, PE], 5.0, 4.4)
        placa = unary_union([circ(P(14.0, 1.8), 3.0), circ(P(20.2, 4.6), 3.0), circ(P(17.0, 5.8), 3.0)]).convex_hull
        sec_am = abanico(P(14.4, -0.4), P(21.4, 2.8), -64, -28, 4, 11.5, 10.5, 4.6, 0.10)
        sec_na = abanico(P(14.0, 0.6), P(21.8, 3.9), -60, -24, 4, 8.6, 7.6, 4.6, 0.10)
        sec_ro = abanico(P(14.2, 2.0), P(20.6, 4.6), -58, -34, 3, 5.8, 5.4, 4.8, 0.12)
        b.add("amarillo", f(sec_am))
        b.add("naranja", f(sec_na))
        b.add("rojo", f(unary_union([hueso, placa, sec_ro])))

        # mano (segmento exterior): primarias en abanico hacia arriba/afuera
        PH = P(28.0, 15.0)
        mano_hueso = trazo([PE, PH], 5.0, 4.4)
        prim_am = abanico(P(25.6, 11.8), P(26.6, 19.4), 6, 84, 6, 12.5, 12.0, 4.6, 0.10)
        prim_na = abanico(P(25.2, 12.4), P(25.8, 18.6), 12, 88, 5, 9.0, 8.2, 4.6, 0.10)
        cob_ro = unary_union([
            abanico(P(24.6, 12.8), P(24.4, 17.0), 18, 86, 4, 5.8, 5.4, 4.8, 0.14),
            mano_hueso,
            unary_union([circ(P(26.0, 14.6), 3.4), circ(PE + P(1.5, 1.8), 3.0)]).convex_hull,
        ])
        m.add("amarillo", f(prim_am))
        m.add("naranja", f(prim_na))
        m.add("rojo", f(cob_ro))

    # ---------- COLA (llamas)
    PC = P(0, -13.4)
    cola_am = unary_union([
        pluma(P(-2.6, -17.0), -122, 16.5, 4.8, curva=-0.18),
        pluma(P(-1.4, -17.5), -104, 19.5, 4.8, curva=0.14),
        pluma(P(0.6, -17.5), -86, 21.0, 4.8, curva=-0.14),
        pluma(P(1.8, -17.5), -70, 18.5, 4.8, curva=0.16),
        pluma(P(2.6, -17.0), -55, 15.5, 4.8, curva=0.18),
    ])
    cola_na = unary_union([
        pluma(P(-2.2, -17.0), -114, 13.0, 4.8, curva=-0.18),
        pluma(P(-0.6, -17.5), -96, 15.0, 4.8, curva=0.16),
        pluma(P(1.0, -17.5), -78, 14.5, 4.8, curva=-0.12),
        pluma(P(2.2, -17.0), -62, 12.5, 4.8, curva=0.18),
    ])
    cola_ro = unary_union([
        pluma(P(-1.6, -17.0), -108, 8.5, 5.0, curva=-0.14),
        pluma(P(0.0, -17.2), -90, 10.0, 5.0, curva=0.10),
        pluma(P(1.6, -17.0), -72, 8.5, 5.0, curva=0.14),
        unary_union([circ(P(-2.0, -18.0), 2.3), circ(P(2.0, -18.0), 2.3), circ(P(0, -19.5), 2.8)]).convex_hull,
    ])
    cola.add("amarillo", cola_am)
    cola.add("naranja", cola_na)
    cola.add("rojo", cola_ro)

    # ---------- BISAGRAS (A = pivote, B = anillo)
    juntas = []
    juntas.append(bisagra(cuerpo, cola, PC, (0, 1)))
    for s in "DI":
        k = 1 if s == "D" else -1
        ps, pe = PS * [k, 1], PE * [k, 1]
        juntas.append(bisagra(cuerpo, hombro[s], ps, (-k * 1.0, -0.15)))
        juntas.append(bisagra(hombro[s], mano[s], pe, ps - pe))

    # ---------- HOLGURAS entre piezas (prioridad: cuerpo > brazo > mano; cuerpo > cola)
    def separar(alta, baja):
        baja.recortar(alta.contorno().buffer(G, 8))

    separar(cuerpo, cola)
    for s in "DI":
        separar(cuerpo, hombro[s])
        separar(hombro[s], mano[s])
        separar(cuerpo, mano[s])
        separar(cola, hombro[s])

    piezas = [cuerpo, cola, hombro["D"], hombro["I"], mano["D"], mano["I"]]
    return piezas, juntas


# ---------------------------------------------------------------- sólidos por color
def solidos(piezas, eco=False):
    """Devuelve {color: Manifold} (todas las piezas juntas, sin solapes entre colores)."""
    por_color = {c: [] for c in COLORES}
    for p in piezas:
        regs = p.regiones()
        # sólidos 3D rojos (pivotes y anillos) tapan a las regiones 2D
        huella = unary_union(p.huella_extra) if p.huella_extra else Polygon()
        rojo3d = mf.Manifold.batch_boolean(p.pin3d, mf.OpType.Add) if p.pin3d else mf.Manifold()
        for color, g, h in regs:
            g = limpia(g.difference(huella))
            if g.is_empty:
                continue
            if eco and color != "rojo":
                z0 = min(BASE_ECO, h - 0.8)
                por_color["rojo"].append(extruir(g, z0))
                por_color[color].append(extruir(g, h, z0))
            elif color == "negro":
                por_color["rojo"].append(extruir(g, h - 0.8))
                por_color["negro"].append(extruir(g, h, h - 0.8))
            else:
                por_color[color].append(extruir(g, h))
        por_color["rojo"].append(rojo3d)
    out = {}
    for c, lst in por_color.items():
        lst = [x for x in lst if not x.is_empty()]
        out[c] = mf.Manifold.batch_boolean(lst, mf.OpType.Add) if lst else mf.Manifold()
    # garantizar que no hay solape entre colores (prioridad: negro > amarillo > naranja > rojo)
    orden = ["negro", "amarillo", "naranja", "rojo"]
    acum = mf.Manifold()
    for c in orden:
        out[c] = out[c] - acum
        acum = acum + out[c]
    return out


if __name__ == "__main__":
    import salida
    salida.main(sys.argv[1:])
