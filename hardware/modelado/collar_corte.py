"""
Paso 2 del collar: separa el collar del pecho (dos cuerdas + amarres + dije) como pieza aparte.

- Corte al pie de los nudos que marcó Bru: izquierda el amarre doble (z≈230), derecha el anillo doble (z≈239).
  El nudo queda en el cuerpo con un CASQUILLO de 1 mm: la cuerda entra en él y la unión queda escondida.
- Cuerda = tubo r 1,3 mm alrededor del eje + la hebra delgada pegada (vóxeles 0,1 mm, componentes que no
  llegan a la superficie del pecho) + los amarres que quedan por debajo del corte (r 2,05 en esas zonas).
- Cuerpo = cuerpo hueco − (lo mismo + 0,1 mm de holgura): queda el CANAL donde se pega la cuerda.
Uso: python collar_corte.py cuervo_reparado.stl cuerpo.stl ejes_fino.npz salida   (usa hebras.npz de la misma carpeta)
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
sol_f, cue_f, ej_f, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
RC, RB, RS, VOX, HOLG, CASQ = 1.30, 2.05, 2.8, 0.1, 0.10, 1.0
NUDO_Z = {"izq": 230.0, "der": 239.0}    # nudo elegido (se busca su canto inferior cerca de esta altura)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
sol_t = trimesh.load_mesh(sol_f, process=True); SOL = man(sol_t)
CUE = man(trimesh.load_mesh(cue_f, process=True)); E = np.load(ej_f); H = np.load(Path(ej_f).parent / 'hebras.npz')
RH = 0.72   # hebra r 0,55 + margen

def remuestrear(p, paso):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]; t = np.arange(0, s[-1] + 1e-9, paso)
    return np.column_stack([np.interp(t, s, p[:, k]) for k in range(3)]), t

def marcos(p):
    T = np.gradient(p, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = [np.cross(T[0], [0, 1, 0])]; U[0] /= np.linalg.norm(U[0])
    for i in range(1, len(p)):
        u = U[-1] - T[i] * (U[-1] @ T[i]); U.append(u / np.linalg.norm(u))
    U = np.array(U); return T, U, np.cross(T, U)

def tubo(p, rad, n=40):
    T, U, W = marcos(p); a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = (p[:, None, :] + rad[:, None, None] * (np.cos(a)[None, :, None] * U[:, None, :] + np.sin(a)[None, :, None] * W[:, None, :])).reshape(-1, 3)
    N = len(p); F = []
    for i in range(N - 1):
        for j in range(n):
            a0, a1, b0, b1 = i * n + j, i * n + (j + 1) % n, (i + 1) * n + j, (i + 1) * n + (j + 1) % n
            F += [[a0, b0, b1], [a0, b1, a1]]
    V = np.vstack([V, p[0], p[-1]]); c0, c1 = len(V) - 2, len(V) - 1
    for j in range(n):
        F += [[c0, j, (j + 1) % n], [c1, (N - 1) * n + (j + 1) % n, (N - 1) * n + j]]
    t = trimesh.Trimesh(V, F, process=True)
    if t.volume < 0: t.invert()
    return man(t)

def cobertura(p, T, U, W, lo, hi):
    """Fracción del contorno con material entre lo y hi del eje (detecta amarres)."""
    c = []
    for i in range(len(p)):
        s = sol_t.section(plane_normal=T[i], plane_origin=p[i])
        if s is None: c.append(0); continue
        P = np.vstack(s.discrete) - p[i]; q = np.c_[P @ U[i], P @ W[i]]; r = np.linalg.norm(q, axis=1)
        a = np.arctan2(q[:, 1], q[:, 0])[(r > lo) & (r < hi)]
        c.append(len(np.unique(np.floor((a + np.pi) / (np.pi / 18)))) / 36)
    return np.array(c)

CUT, CUT_H, info = None, None, {}
for k in ("izq", "der"):
    p = H[k + '_eje']; T, U, W = marcos(p)   # eje reajustado (mismas estaciones cada 0,25 mm)
    cob = cobertura(p, T, U, W, 1.45, 2.1)
    zona = np.abs(p[:, 2] - NUDO_Z[k]) < 3.0
    i_n = np.nonzero(zona & (cob > 0.34))[0][0]           # canto inferior del nudo
    i_cut = i_n - 1
    # amarres por debajo del corte: van con el collar
    amarre = (cob > 0.34); amarre[i_cut:] = False
    amarre = ndimage.binary_dilation(amarre, iterations=3)
    pc = p[:i_cut + 1]
    # prolongar 1 mm dentro del nudo (casquillo)
    ext = pc[-1] + T[i_cut] * np.arange(0.25, CASQ + 1e-6, 0.25)[:, None]
    # prolongar 2 mm hacia abajo (la cuerda ya cuelga libre)
    ini = pc[0] - T[0] * np.arange(2.0, 0, -0.25)[:, None]
    pt = np.vstack([ini, pc, ext]); rad = np.r_[np.full(len(ini), RC), np.where(amarre[:i_cut + 1], RB, RC), np.full(len(ext), RC)]
    info[k] = {"corte_z": round(float(p[i_cut, 2]), 2), "amarres_z": [round(float(z), 1) for z in p[:i_cut + 1][np.diff(np.r_[0, amarre[:i_cut + 1].astype(int)]) == 1][:, 2]]}
    # --- hebra delgada: vóxeles alrededor del eje (hasta el corte) que no tocan el pecho
    lo, hi = pc.min(0) - RS - 0.5, pc.max(0) + RS + 0.5
    g = [np.arange(lo[d], hi[d], VOX) for d in range(3)]
    G = np.stack(np.meshgrid(*g, indexing="ij"), -1).reshape(-1, 3)
    pd, sd = remuestrear(pc, 0.05); dd, jj = cKDTree(pd).query(G, workers=-1)
    cerca = (dd < RS) & (jj > 0) & (jj < len(pd) - 1)
    idx = np.nonzero(cerca)[0]
    dentro = np.zeros(len(G), bool); dentro[idx] = sol_t.contains(G[idx])
    sh = (G.shape[0],); D = dd.reshape([len(x) for x in g]); IN = dentro.reshape(D.shape); C = cerca.reshape(D.shape)
    cap = IN & (D >= RC - 0.05) & C
    lab, n = ndimage.label(cap, structure=np.ones((3, 3, 3)))
    toca = np.unique(lab[cap & (D > RS - 0.3)])
    extra = cap & ~np.isin(lab, toca)
    print(k, "componentes", n, "hebra/extra vóxeles", int(extra.sum()), flush=True)
    piezas = []
    for dil, nombre in ((1, "c"), (2, "h")):
        ex = ndimage.binary_dilation(extra, iterations=dil)
        if ex.sum() > 20:
            vv, ff, _, _ = marching_cubes(np.pad(ex, 1).astype(np.float32), 0.5)
            mt = trimesh.Trimesh(vv * VOX + lo - VOX, ff, process=True)
            mt = max(mt.split(only_watertight=False), key=len) if False else mt
            trimesh.repair.fix_normals(mt); EX = man(mt)
        else:
            EX = mf.Manifold()
        TB = tubo(pt, rad + (HOLG if nombre == "h" else 0.0))
        hb = H[k][:i_cut + 1]; ej = p[:i_cut + 1]
        for f in (0.33, 0.66, 1.0):      # envolvente cuerda + hebra (rellena el filete entre las dos)
            ph = ej + (hb - ej) * f; ph = np.vstack([ph[0] - (ph[1] - ph[0]) / np.linalg.norm(ph[1] - ph[0]) * np.arange(2.0, 0, -0.25)[:, None], ph])
            rr = RC + (RH - RC) * f + (HOLG if nombre == "h" else 0.0)
            TB = TB + tubo(ph, np.full(len(ph), rr), 32)
        piezas.append(TB + EX)
    CUT = piezas[0] if CUT is None else CUT + piezas[0]
    CUT_H = piezas[1] if CUT_H is None else CUT_H + piezas[1]
print(json.dumps(info), flush=True)
# collar = sólido ∩ cortador  +  lo que queda suelto (dije y cuerdas libres)
A = SOL - CUT; partes = sorted(A.decompose(), key=lambda q: -q.volume())
sueltos = [q for q in partes[1:] if q.volume() > 0.05]
collar = SOL ^ CUT
for q in sueltos: collar = collar + q
cp = sorted(collar.decompose(), key=lambda q: -q.volume())
print("collar piezas", [round(q.volume(), 1) for q in cp[:5]], "sueltos agregados", len(sueltos), flush=True)
cuerpo = CUE - CUT_H; bp = sorted(cuerpo.decompose(), key=lambda q: -q.volume())
print("cuerpo piezas", [round(q.volume(), 2) for q in bp[:6]], flush=True)
tm(cp[0]).export(out / "collar.stl"); tm(bp[0]).export(out / "cuerpo_sin_collar.stl")
for i, q in enumerate(cp[1:4]): tm(q).export(out / f"collar_resto{i}.stl")
info["collar_mm3"] = round(cp[0].volume(), 1); info["cuerpo_mm3"] = round(bp[0].volume(), 1)
json.dump(info, open(out / "collar.json", "w"), indent=1)
