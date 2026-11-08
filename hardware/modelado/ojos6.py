"""
Ojos paso 2b: insertos de resina transparente a partir de los ojos ya alisados (esferas perfectas).

  - Contorno: borde real donde la esfera se encuentra con el párpado (caras de la cabeza alisada
    que están sobre la esfera).
  - Por fuera: la esfera lisa, calculada exacta.
  - Por dentro: iris procedimental (iris.py): fibras, collarete y pupila en relieve;
    el derecho es su espejo.
  - Reborde por dentro (no se sale) + bolsillo del LED (Ø 8,9 × 2,6 mm medido) en la cabeza.

Uso: python ojos5.py cabeza_ojos_lisos.stl cuervo_reparado.stl "forma preliminar.stl" globos.json espejo.json salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
import iris, os
ESTILO = os.environ.get("IRIS", "fibras")
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

T, HOLG, PARED, REB, T_REB = 1.0, 0.10, 0.6, 1.4, 1.0
LED_D, HOLG_LED, BOSS_EXTRA, BOSS_FONDO = 8.9, 0.15, 2.0, 11.0
LED_CUERPO, LED_AIRE, VENTANA_D = 1.6, 0.3, 7.2
TRAS_PCB = 1.5                              # mm detrás del PCB dentro del porta-LED (los ojos casi se tocan por dentro)
R_PORTA = LED_D / 2 + 0.15 + 1.2          # radio del porta-LED: cámara + pared de 1,2 mm   # 5050 de 1,6 mm de alto; 0,3 mm de aire hasta el reborde; ventana para cualquier giro
NS, NT0, NT = 150, 120, 720
cab_f, sol_f, orig_f, gl_f, esp_f, out = sys.argv[1:7]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
cab_t = trimesh.load_mesh(cab_f, process=True); CAB = man(cab_t)
SOL = man(trimesh.load_mesh(sol_f, process=True)); orig = trimesh.load_mesh(orig_f, process=True)
G = json.load(open(gl_f))["der"]; E = json.load(open(esp_f))
cR = np.array(G["centro_esfera"]); rR = G["radio"] + 0.28
cLs = cR.copy(); cLs[0] = 2 * E["X0"] - cLs[0]; cLs += np.array(E["traslacion"]) + np.array([-0.4, -0.4, 0.0]); rL = G["radio"]
ESF = {"izq": (cLs, rL), "der": (cR, rR)}


def region_esfera(cen, r):
    cc = cab_t.triangles_center
    sel = np.nonzero((np.abs(np.linalg.norm(cc - cen, axis=1) - r) < 0.03) & (np.linalg.norm(cc - cen, axis=1) < r + 1))[0]
    sub = cab_t.submesh([sel], append=True)
    adj = sub.face_adjacency; F = len(sub.faces)
    nc, lab = connected_components(coo_matrix((np.ones(len(adj)), (adj[:, 0], adj[:, 1])), shape=(F, F)), directed=False)
    big = np.argmax(np.bincount(lab, sub.area_faces))
    return sub.submesh([np.nonzero(lab == big)[0]], append=True)


def marco(g, cen):
    ar = g.area_faces; c0 = ar @ g.triangles_center / ar.sum()
    e = c0 - cen; e /= np.linalg.norm(e)
    x = np.cross([0, 0, 1], e); x /= np.linalg.norm(x); y = np.cross(e, x)
    return c0, e, x, y


def contorno(g, c, x, y):
    b = trimesh.grouping.group_rows(g.edges_sorted, require_count=1)
    P = g.vertices[np.unique(g.edges_sorted[b])] - c
    th = np.arctan2(P @ y, P @ x); rr = np.hypot(P @ x, P @ y)
    ts = np.linspace(-np.pi, np.pi, NT0, endpoint=False)
    R = np.array([np.percentile(rr[np.abs((th - t + np.pi) % (2 * np.pi) - np.pi) < 0.08], 60) for t in ts])
    k = 2; Rp = np.r_[R[-k:], R, R[:k]]; R = np.convolve(Rp, np.ones(2 * k + 1) / (2 * k + 1), "valid")
    tf = np.linspace(-np.pi, np.pi, NT, endpoint=False)
    return tf, np.interp(tf, np.r_[ts, ts[0] + 2 * np.pi], np.r_[R, R[0]], period=2 * np.pi)


def h_esfera(pts, c, e, x, y, cen, r):
    q = c + np.outer(pts[:, 0], x) + np.outer(pts[:, 1], y) - cen
    b = q @ e; disc = b ** 2 - (q * q).sum(1) + r ** 2
    return -b + np.sqrt(np.maximum(disc, 0))


def h_malla(m, pts, c, e, x, y):
    o = c + np.outer(pts[:, 0], x) + np.outer(pts[:, 1], y) + e * 20
    L, I, _ = m.ray.intersects_location(o, np.tile(-e, (len(o), 1)), multiple_hits=False)
    h = np.full(len(o), np.nan); h[I] = (L - c) @ e; return h


fr = {}
for nom in ("izq", "der"):
    cen, r = ESF[nom]; g = region_esfera(cen, r)
    c, e, x, y = marco(g, cen); ts, R = contorno(g, c, x, y)
    fr[nom] = (cen, r, g, c, e, x, y, ts, R)
    g.export(out / f"globo_visible_{nom}.stl")
# relieve del iris en el marco del ojo izquierdo (original tallado menos la esfera)
cenL, rL_, _, cL, eL, xL, yL, _, _ = fr["izq"]
info, cabeza = {}, CAB
for nom in ("izq", "der"):
    cen, r, g, c, e, x, y, ts, R = fr[nom]
    pts = np.array([(0.0, 0.0)] + [(rv * s * np.cos(t), rv * s * np.sin(t)) for s in np.linspace(0, 1, NS + 1)[1:] for t, rv in zip(ts, R)])
    Hout = h_esfera(pts, c, e, x, y, cen, r)
    sfr = np.r_[0.0, np.repeat(np.linspace(0, 1, NS + 1)[1:], NT)]
    rel = -iris.grosor(pts[:, 0], pts[:, 1], espejo=(nom == "der"), estilo=ESTILO) * (1 - iris._ss(0.90, 0.985, sfr))
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
    M = np.column_stack([x, y, e, c])
    sec = lambda off: mf.CrossSection([[(float((rv + off) * np.cos(t)), float((rv + off) * np.sin(t))) for t, rv in zip(ts, R)]])
    ext = lambda off, z0, z1: mf.Manifold.extrude(sec(off), z1 - z0).translate([0, 0, z0]).transform(M)
    borde_in = float(np.min(Hin[-NT:])); zr = float(np.min(Hin)) - 1.6
    esf_o = mf.Manifold.sphere(r, 384).translate(list(cen))
    pared = (ext(0, zr, 8) - ext(-PARED, zr - 1, 9)) ^ esf_o - mf.Manifold(sh.__class__ and man(sh)) if False else (ext(0, zr, 8) - ext(-PARED, zr - 1, 9)) ^ esf_o   # sube hasta la cúpula
    reborde = (ext(REB, zr - T_REB, zr) - ext(-PARED, zr - 2, zr + 1)) ^ SOL.translate(list(-e * 0.8))
    inserto = capa + pared + reborde
    partes = inserto.decompose(); inserto = max(partes, key=lambda q: q.volume()); zl = zr - T_REB
    print(nom, 'trozos del inserto (mm³):', sorted([round(q.volume(), 1) for q in partes], reverse=True)[:4], flush=True)
    rb = float(R.max()) + REB + BOSS_EXTRA
    z_pcb = zl - LED_AIRE - LED_CUERPO          # cara del PCB: tope donde asienta el módulo
    z_fondo = z_pcb - 1.0 - TRAS_PCB            # fondo del boss: PCB (1 mm) + espacio para soldaduras
    boss = mf.Manifold.cylinder(zr + 2 - z_fondo, rb, rb, 128).translate([0, 0, z_fondo]).transform(M) ^ SOL
    zl = zr - T_REB
    bola = mf.Manifold.sphere(r + 0.03, 384).translate(list(cen))
    cil = lambda rad, z0, z1: mf.Manifold.cylinder(z1 - z0, rad, rad, 128).translate([0, 0, z0]).transform(M)
    # Perforación del boss con forma de reborde + círculo del porta-LED: el inserto entra por DENTRO
    sec_b = (sec(REB + HOLG) + mf.CrossSection.circle(R_PORTA + HOLG, 128))
    ext_b = lambda s, z0, z1: mf.Manifold.extrude(s, z1 - z0).translate([0, 0, z0]).transform(M)
    hueco = ((ext(HOLG, zr - 0.01, 8) ^ bola) + ext(REB + HOLG, zl - 0.01, zr + 0.01)
             + ext_b(sec_b, z_fondo - 3, zl + 0.01))
    # Porta-LED: tapón que llena la perforación, aprieta el reborde y sostiene el módulo
    porta = (ext_b(sec_b.offset(-HOLG - 0.1, mf.JoinType.Round), z_fondo, zl)
             - cil(VENTANA_D / 2, z_pcb - 0.01, zl + 1)                     # ventana de luz
             - cil(LED_D / 2 + HOLG_LED, z_fondo - 1, z_pcb))               # cámara del PCB (tope en z_pcb)
    tm(porta).export(out / f"porta_led_{nom}.stl")
    cabeza = (cabeza + boss) - hueco
    tm(inserto).export(out / f"ojo_{nom}.stl")
    info[nom] = {"contorno_mm": [round(float(2 * R.min()), 2), round(float(2 * R.max()), 2)],
                 "grosor_mm": [round(float(np.min(Hout - Hin)), 2), round(float(np.max(Hout - Hin)), 2)],
                 "volumen_mm3": round(inserto.volume(), 1), "marco": {"c": c.tolist(), "e": e.tolist(), "x": x.tolist(), "y": y.tolist(), "zr": zr, "zl": zl, "z_pcb": z_pcb, "z_fondo": z_fondo}, "trozos_descartados": len(partes) - 1}
    print(nom, info[nom], flush=True)
cab = max(cabeza.decompose(), key=lambda q: q.volume())
tm(cab).export(out / "cabeza_ojos.stl")
(out / "ojos.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print("listo")
