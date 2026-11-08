"""
Ojos v4: tomados del ojo liso esculpido (derecho) y su espejo (izquierdo).

  - Contorno: borde exacto del globo ocular (globo_esfera.py), no un óvalo.
  - Por fuera: la superficie real del globo liso.
  - Por dentro: el iris tallado del ojo izquierdo original, en relieve (más resina = más oscuro).
  - Reborde por dentro + bolsillo del LED (Ø 8,9 × 2,6 mm medido) en la cabeza.

Uso: python ojos4.py cabeza.stl "forma preliminar.stl" carpeta_globos(espejo) salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

T, HOLG, PARED, REB, T_REB = 1.0, 0.10, 0.6, 1.4, 1.0
LED_D, HOLG_LED, BOSS_EXTRA, BOSS_FONDO = 8.9, 0.2, 2.0, 11.0
NS, NT = 16, 96
cab_f, orig_f, gl_d, out = sys.argv[1:5]; gl_d, out = Path(gl_d), Path(out); out.mkdir(parents=True, exist_ok=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
CAB = man(trimesh.load_mesh(cab_f, process=True)); print('CAB', CAB.status(), CAB.volume())
orig = trimesh.load_mesh(orig_f, process=True)
SOL = man(trimesh.load_mesh(str(Path(orig_f).parent / 'modelado' / 'cuervo_reparado.stl'), process=True)); print('SOL', SOL.status())
X0 = json.load(open(gl_d / "espejo.json"))["X0"]


def marco(g):
    ar = g.area_faces; c = ar @ g.triangles_center / ar.sum()
    e = ar @ g.face_normals; e /= np.linalg.norm(e)
    x = np.cross([0, 0, 1], e); x /= np.linalg.norm(x); y = np.cross(e, x)
    return c, e, x, y


def contorno(g, c, e, x, y):
    """Radio del borde del globo por ángulo (contorno estrellado desde el centro)."""
    bordes = trimesh.grouping.group_rows(g.edges_sorted, require_count=1)
    P = g.vertices[np.unique(g.edges_sorted[bordes])] - c
    px, py = P @ x, P @ y
    th = np.arctan2(py, px); rr = np.hypot(px, py)
    ts = np.linspace(-np.pi, np.pi, NT, endpoint=False)
    R = np.array([np.median(rr[np.abs((th - t + np.pi) % (2 * np.pi) - np.pi) < 0.12]) for t in ts])
    k = 3; Rp = np.r_[R[-k:], R, R[:k]]
    return ts, np.convolve(Rp, np.ones(2 * k + 1) / (2 * k + 1), "valid")


def alturas(malla, c, e, x, y, pts2):
    q = [c + x * px + y * py + e * 20 for px, py in pts2]
    L, I, _ = malla.ray.intersects_location(q, [-e] * len(q), multiple_hits=False)
    h = np.full(len(q), np.nan); h[I] = (L - c) @ e; return h


# Relieve del iris: ojo izquierdo original menos el globo liso espejado, en el marco del ojo izquierdo
gL = trimesh.load_mesh(gl_d / "globo_izq.stl", process=True)
cL, eL, xL, yL = marco(gL)
info, cabeza = {}, CAB
for nom in ("izq", "der"):
    g = trimesh.load_mesh(gl_d / f"globo_{nom}.stl", process=True)
    c, e, x, y = marco(g)
    ts, R = contorno(g, c, e, x, y)
    R = R - HOLG
    pts = [(0.0, 0.0)] + [(r * s * np.cos(t), r * s * np.sin(t)) for s in np.linspace(0, 1, NS + 1)[1:] for t, r in zip(ts, R)]
    pts = np.array(pts)
    Hout = alturas(g, c, e, x, y, pts)
    Hout = np.where(np.isfinite(Hout), Hout, np.nanmin(Hout))
    # relieve: mismo punto relativo en el ojo izquierdo (espejado en x para el derecho)
    pr = pts.copy()
    if nom == "der": pr[:, 0] *= -1
    Ho = alturas(orig, cL, eL, xL, yL, pr); Hs = alturas(gL, cL, eL, xL, yL, pr)
    rel = np.clip(np.nan_to_num(Ho - Hs, nan=0.0), -1.2, 0.0)
    Hin = Hout - T + rel
    P3 = lambda h: c + np.outer(pts[:, 0], x) + np.outer(pts[:, 1], y) + np.outer(h, e)
    N = len(pts); idx = lambda si, ti: 1 + si * NT + (ti % NT)
    F = []
    for ti in range(NT):
        F.append([0, idx(0, ti), idx(0, ti + 1)])
        for si in range(NS - 1):
            F += [[idx(si, ti), idx(si + 1, ti), idx(si + 1, ti + 1)], [idx(si, ti), idx(si + 1, ti + 1), idx(si, ti + 1)]]
    F = np.array(F); W = []
    for ti in range(NT):
        a, b = idx(NS - 1, ti), idx(NS - 1, ti + 1); W += [[a, b, b + N], [a, b + N, a + N]]
    sh = trimesh.Trimesh(np.vstack([P3(Hout), P3(Hin)]), np.vstack([F, F[:, ::-1] + N, W]), process=True)
    trimesh.repair.fix_normals(sh)
    if sh.volume < 0: sh.invert()
    capa = man(sh)
    print(nom, "capa", capa.status(), round(capa.volume(),1), "R", R.min().round(2), R.max().round(2), "nan Hout", np.isnan(alturas(g, c, e, x, y, pts)).sum(), flush=True)
    # sección del contorno para paredes, reborde y agujero
    def seccion(off):
        return mf.CrossSection([[(float((r + off) * np.cos(t)), float((r + off) * np.sin(t))) for t, r in zip(ts, R)]])
    M = np.column_stack([x, y, e, c])
    ext = lambda off, z0, z1: mf.Manifold.extrude(seccion(off), z1 - z0).translate([0, 0, z0]).transform(M)
    borde_in = float(np.min(Hin[-NT:])); zr = float(np.min(Hin)) - 1.6
    pared = (ext(0, zr, borde_in + 0.3) - ext(-PARED, zr - 1, borde_in + 1.3)) ^ SOL.translate(list(-e * 0.4))
    reborde = (ext(REB, zr - T_REB, zr) - ext(-PARED, zr - 2, zr + 1)) ^ SOL.translate(list(-e * 0.8))
    inserto = capa + pared + reborde
    partes = inserto.decompose(); inserto = max(partes, key=lambda q: q.volume())
    rb = float(R.max()) + REB + BOSS_EXTRA
    boss = mf.Manifold.cylinder(BOSS_FONDO, rb, rb, 96).translate([0, 0, zr - BOSS_FONDO + 2]).transform(M) ^ SOL
    zl = zr - T_REB
    hueco = (ext(HOLG, zr - 0.01, 8) + ext(REB + HOLG, zl - 0.01, zr + 0.01)
             + mf.Manifold.cylinder(BOSS_FONDO + 2, LED_D / 2 + HOLG_LED, LED_D / 2 + HOLG_LED, 96).translate([0, 0, zl - BOSS_FONDO - 1]).transform(M))
    cabeza = (cabeza + boss) - hueco
    tm(inserto).export(out / f"ojo_{nom}.stl")
    info[nom] = {"ancho_mm": round(float(2 * R.min()), 2), "largo_mm": round(float(2 * R.max()), 2),
                 "grosor_min_mm": round(float(np.min(Hout - Hin)), 2), "grosor_max_mm": round(float(np.max(Hout - Hin)), 2),
                 "volumen_mm3": round(inserto.volume(), 1), "trozos_descartados": len(partes) - 1}
    print(nom, info[nom], flush=True)
tm(cabeza).export(out / "cabeza_ojos.stl")
info["cabeza_trozos"] = sum(q.volume() > 1 for q in cabeza.decompose())
(out / "ojos.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print("listo", info["cabeza_trozos"])
