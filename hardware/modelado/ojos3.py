"""
Ojos v3: insertos ovalados con el contorno real de cada globo ocular (elipses medidas en la vista
a lo largo del eje de cada ojo, elipses.json).

  - Por fuera: casquete liso (esfera ajustada al globo, levantada hasta el percentil 90 del relieve).
  - Por dentro: el relieve esculpido copiado T_BASE mm hacia adentro (más resina = más oscuro).
  - Pared y reborde ovalados; se meten desde el interior de la cabeza.
  - Cabeza: agujero ovalado ajustado, refuerzo interior con asiento del reborde y bolsillo del LED
    (PCB Ø 8,9 × 2,6 mm medido), abierto hacia el interior para los cables.

Uso: python ojos3.py cabeza.stl cuervo_reparado.stl elipses.json salida_dir
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

T_BASE, HOLG, PARED = 1.4, 0.10, 0.6
UMB_PARPADO = float(__import__("os").environ.get("UMB", "0.25"))
REB, T_REB, PROF_REB = 1.6, 1.0, 4.3       # ancho y grosor del reborde; cara exterior a 4,3 mm bajo el ápice
LED_D, LED_T, HOLG_LED = 8.9, 2.6, 0.2
BOSS_EXTRA, BOSS_FONDO = 2.2, 11.0
EJES = {"izq": ((-11.83, -64.28, 267.79), (-0.8261, -0.3428, -0.4472)),
        "der": ((17.48, -64.42, 268.01), (0.9142, -0.2308, -0.3332))}

cab_f, sol_f, eli_f, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
E = json.load(open(eli_f))
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
CAB = man(trimesh.load_mesh(cab_f, process=True))
sol_t = trimesh.load_mesh(sol_f, process=True); SOL = man(sol_t)


def eli(a, b, z0, z1, M, seg=128):
    """Cilindro elíptico (semi-ejes a, b) entre z0 y z1 en el marco M."""
    return mf.Manifold.cylinder(z1 - z0, 1.0, 1.0, seg).scale([a, b, 1]).translate([0, 0, z0]).transform(M)


info, cabeza = {}, CAB
for nom, (c, e) in EJES.items():
    p = E[nom]; c = np.array(c); e = np.array(e) / np.linalg.norm(e); f = -e
    # ejes de imagen reales de la vista donde se midieron las elipses (ejes_vista.json)
    VJ = json.load(open(Path(eli_f).parent / "ejes_vista.json"))[nom]
    r = np.array(VJ["derecha"]); u = np.array(VJ["arriba"])
    rot = np.radians(p["rot"]); x = np.cos(rot) * r + np.sin(rot) * u; y = np.cross(e, x)
    o = c + r * p["cx"] + u * p["cy"]
    a, b = p["a"], p["b"]
    # Ajuste automático: encoger la elipse hasta que su borde no suba al párpado
    # (párpado = superficie más de 0,5 mm por encima del paraboloide ajustado al centro del globo)
    def alturas(sa, sb, s_, t_):
        q = [o + x * sa * sv * np.cos(tv) + y * sb * sv * np.sin(tv) + e * 15 for sv, tv in zip(s_, t_)]
        L, R_, _ = sol_t.ray.intersects_location(q, [f] * len(q), multiple_hits=False)
        h = np.full(len(q), np.nan); h[R_] = (L - o) @ e; return h
    sc_ = np.repeat(np.linspace(0.1, 0.6, 6), 36); tc_ = np.tile(np.linspace(0, 2 * np.pi, 36, endpoint=False), 6)
    hc = alturas(a, b, sc_, tc_); okc = np.isfinite(hc)
    XYc = np.c_[a * sc_ * np.cos(tc_), b * sc_ * np.sin(tc_)]
    Ac = np.c_[np.ones(okc.sum()), XYc[okc], XYc[okc] ** 2, XYc[okc, 0] * XYc[okc, 1]]
    cc_ = np.linalg.lstsq(Ac, hc[okc], rcond=None)[0]
    tr = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    for k in np.linspace(1.0, 0.55, 46):
        hr_ = alturas(a * k, b * k, np.ones(72), tr)
        XYr = np.c_[a * k * np.cos(tr), b * k * np.sin(tr)]
        pr = np.c_[np.ones(72), XYr, XYr ** 2, XYr[:, 0] * XYr[:, 1]] @ cc_
        if np.nanmax(hr_ - pr) < UMB_PARPADO:
            break
    a, b = a * k, b * k
    print(nom, f"elipse escalada x{k:.2f}", flush=True)
    # alturas de la superficie del globo en una rejilla polar dentro de la elipse
    NS, NT = 14, 72
    ss = np.linspace(0, 1, NS + 1)[1:]; ts = np.linspace(0, 2 * np.pi, NT, endpoint=False)
    XY = [(0.0, 0.0)] + [(a * sv * np.cos(t), b * sv * np.sin(t)) for sv in ss for t in ts]
    orig = [o + x * px + y * py + e * 15 for px, py in XY]
    H = np.full(len(XY), np.nan)
    loc, ri, _ = sol_t.ray.intersects_location(orig, [f] * len(orig), multiple_hits=False)
    H[ri] = (loc - o) @ e - 0.0 + ((np.array(orig)[ri] - o) @ e - 15) * 0  # altura sobre el plano por o
    H[ri] = [((pp - o) @ e) for pp in loc]
    XYa = np.array(XY); ok = np.isfinite(H)
    # superficie exterior lisa: paraboloide por mínimos cuadrados, levantado al percentil 80
    Aq = np.c_[np.ones(ok.sum()), XYa[ok], XYa[ok] ** 2, XYa[ok, 0] * XYa[ok, 1]]
    cq = np.linalg.lstsq(Aq, H[ok], rcond=None)[0]
    Hq = np.c_[np.ones(len(XYa)), XYa, XYa ** 2, XYa[:, 0] * XYa[:, 1]] @ cq
    res = H - Hq; Hq += np.nanpercentile(res, 95)   # casquete liso que cubre el relieve
    H = np.where(ok, H, Hq)
    Hin = np.minimum(H - T_BASE, Hq - 0.6)            # relieve hacia adentro, al menos 0,6 mm de resina
    # malla cerrada: tapa exterior (Hq), tapa interior (Hin), pared en el borde
    def capa_pts(h):
        return np.array([o + x * px + y * py + e * hz for (px, py), hz in zip(XY, h)])
    Vo, Vi = capa_pts(Hq), capa_pts(Hin); N = len(XY)
    idx = lambda si, ti: 1 + si * NT + (ti % NT)
    F = []
    for ti in range(NT):
        F.append([0, idx(0, ti), idx(0, ti + 1)])
        for si in range(NS - 1):
            F += [[idx(si, ti), idx(si + 1, ti), idx(si + 1, ti + 1)], [idx(si, ti), idx(si + 1, ti + 1), idx(si, ti + 1)]]
    F = np.array(F)
    Fi = F[:, ::-1] + N
    borde = [idx(NS - 1, ti) for ti in range(NT)]
    W = []
    for ti in range(NT):
        p0_, p1_ = borde[ti], borde[(ti + 1) % NT]
        W += [[p0_, p1_, p1_ + N], [p0_, p1_ + N, p0_ + N]]
    malla = trimesh.Trimesh(np.vstack([Vo, Vi]), np.vstack([F, Fi, np.array(W)]), process=True)
    trimesh.repair.fix_normals(malla)
    if malla.volume < 0: malla.invert()
    capa = man(malla)
    M = np.column_stack([x, y, e, o])
    zr = float(Hin[1 + (NS - 1) * NT:].min()) - 2.4      # reborde 2,4 mm bajo el punto más hondo del borde interior
    print(nom, "capa", capa.status(), round(capa.volume(), 1), "zr", round(zr, 2), flush=True)
    Rs = float("nan")
    ztop = float(Hin[1 + (NS - 1) * NT:].max()) + 0.3
    pared = (eli(a, b, zr, ztop, M) - eli(a - PARED, b - PARED, zr - 1, ztop + 1, M)) ^ SOL   # nunca asoma por fuera
    reborde = eli(a + REB, b + REB, zr - T_REB, zr, M) - eli(a - PARED, b - PARED, zr - 2, zr + 1, M)
    reborde = reborde ^ SOL.translate(list(-e * 0.8))   # nunca asoma: queda ≥ 0,8 mm bajo la superficie
    inserto = capa + pared + reborde
    partes = inserto.decompose(); inserto = max(partes, key=lambda q: q.volume())
    rb = max(a, b) + REB + BOSS_EXTRA
    boss = mf.Manifold.cylinder(BOSS_FONDO - 1, rb, rb, 128).translate([0, 0, -BOSS_FONDO]).transform(M) ^ SOL
    zl = zr - T_REB
    hueco = (eli(a + HOLG, b + HOLG, zr - 0.01, 8, M) + eli(a + REB + HOLG, b + REB + HOLG, zl - 0.01, zr + 0.01, M)
             + mf.Manifold.cylinder(zl + BOSS_FONDO + 1, LED_D / 2 + HOLG_LED, LED_D / 2 + HOLG_LED, 96).translate([0, 0, -BOSS_FONDO - 1]).transform(M))
    cabeza = (cabeza + boss) - hueco
    tm(inserto).export(out / f"ojo_{nom}.stl")
    info[nom] = {"elipse_mm": [2 * a, 2 * b], "reborde_bajo_apice_mm": round(-zr, 2),
                 "volumen_mm3": round(inserto.volume(), 1), "trozos_descartados": len(partes) - 1}
    print(nom, info[nom], flush=True)
tm(cabeza).export(out / "cabeza_ojos.stl")
info["cabeza_trozos"] = sum(q.volume() > 1 for q in cabeza.decompose())
(out / "ojos.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print("listo", info["cabeza_trozos"])
