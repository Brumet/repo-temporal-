"""
Paso 2 del collar (v2): separa el collar del pecho con cortes 2D perpendiculares a cada cuerda.

En cada estación (cada 0,25 mm): sección del sólido → apertura morfológica con disco de r 1,9 mm (quita lo que es
más delgado que el pecho) → lo que se quitó, unido al núcleo, a menos de 2,6 mm del eje = CUERDA (con hebra, filetes
y amarres). Más el núcleo r 1,3 (canal en el pecho = encastre). Se apilan las secciones en coordenadas de la cuerda,
marching cubes y se dobla al espacio real. Al pie del nudo elegido: casquillo de 1 mm dentro del nudo.
Uso: python collar_corte2.py cuervo_reparado.stl cuerpo.stl hebras.npz salida
"""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from scipy import ndimage
from skimage.draw import polygon as dibujar
from skimage.measure import marching_cubes
sol_f, cue_f, hb_f, out = sys.argv[1:5]; out = Path(out); out.mkdir(parents=True, exist_ok=True)
PX, VENT, R_AP, R_MAX, RC, HOLG, CASQ, EXT_INF = 0.05, 7.0, 1.9, 2.35, 1.3, 0.10, 0.6, 2.0   # casquillo 0,6: el nudo mide ~1 mm
NUDO_Z = {"izq": 229.2, "der": 238.7}   # nudos marcados (amarre doble izq, anillo doble der)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(M):
    me = M.to_mesh(); return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False)
sol_t = trimesh.load_mesh(sol_f, process=True); SOL = man(sol_t); CUE = man(trimesh.load_mesh(cue_f, process=True)); H = np.load(hb_f)
n = int(2 * VENT / PX) + 1; ax = np.linspace(-VENT, VENT, n); UU, WW = np.meshgrid(ax, ax, indexing="ij"); RR = np.hypot(UU, WW)
k_ap = int(R_AP / PX); yy, xx = np.mgrid[-k_ap:k_ap + 1, -k_ap:k_ap + 1]; DISCO = xx ** 2 + yy ** 2 <= k_ap ** 2
NUCLEO = RR < RC

def marcos(p):
    T = np.gradient(p, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = [np.cross(T[0], [0, 1, 0])]; U[0] /= np.linalg.norm(U[0])
    for i in range(1, len(p)):
        u = U[-1] - T[i] * (U[-1] @ T[i]); U.append(u / np.linalg.norm(u))
    U = np.array(U); return T, U, np.cross(T, U)

def seccion(p, T, U, W):
    s = sol_t.section(plane_normal=T, plane_origin=p); M = np.zeros((n, n), bool)
    if s is None: return M
    for q in s.discrete:
        a = (q - p) @ U / PX + (n - 1) / 2; b = (q - p) @ W / PX + (n - 1) / 2
        rr, cc = dibujar(a, b, M.shape); M[rr, cc] ^= True
    return M

def cuerda2d(M):
    pad = k_ap + 2; Mp = np.pad(M, pad, mode="edge")
    ab = ndimage.binary_opening(Mp, structure=DISCO)[pad:-pad, pad:-pad]
    c = M & ~ab & (RR < R_MAX)
    lab, nl = ndimage.label(c | NUCLEO); keep = np.unique(lab[RR < 0.8]); keep = keep[keep > 0]
    return np.isin(lab, keep)

CUT, CUT_H, info = [], [], {}
for k in ("izq", "der"):
    p = H[k + "_eje"]; T, U, W = marcos(p)
    pilas, aire = [], []
    cob, rsec, secs = [], [], None
    for i in range(len(p)):
        M = seccion(p[i], T[i], U[i], W[i]); C = cuerda2d(M)
        pilas.append(C); aire.append(~M & (RR < R_MAX + 0.3))
        # radio exterior por sector (24) del contorno a < 3 mm: el nudo es donde la mediana pasa de 1,6 mm
        ang = np.arctan2(WW, UU); sec = np.floor((ang + np.pi) / (np.pi / 12)).astype(int) % 24
        Bd = M & ~ndimage.binary_erosion(M)     # solo el contorno
        rmax = np.array([RR[Bd & (sec == j) & (RR < 3.0)].max() if (Bd & (sec == j) & (RR < 3.0)).any() else 0 for j in range(24)])
        cob.append(np.median(rmax)); rsec.append(rmax); secs = sec
    cob = np.array(cob)
    i_n = np.nonzero((np.abs(p[:, 2] - NUDO_Z[k]) < 1.2) & (cob > 1.6))[0][0]; i_cut = i_n - 1
    info[k] = {"corte_z": round(float(p[i_cut, 2]), 2)}
    # pila: extensión inferior (copia) + estaciones hasta el corte + zona del nudo
    # En el nudo (inclinado): el núcleo sigue como casquillo; la cuerda/hebra sigue solo en los sectores donde
    # el nudo todavía no empieza (radio del contorno < 1,6) → el corte sigue el canto del nudo.
    ne, nc, nn = int(EXT_INF / 0.25), int(CASQ / 0.25), 3
    zona_nudo = []; bloq = np.zeros(24, bool); base = np.maximum(rsec[i_cut], rsec[i_cut - 1])
    for j in range(1, nn + 1):
        i = min(i_cut + j, len(p) - 1); bloq |= (rsec[i] > base + 0.25) | (rsec[i] == 0) | (base > 2.3)   # el contorno crece = empieza el nudo; una vez tapado, queda tapado
        libre = np.isin(secs, np.nonzero(~bloq)[0])
        C = pilas[i] & libre & (RR < 2.2) & (RR > RC - 0.3)
        if j <= nc: C = C | (RR < RC + 0.08)
        zona_nudo.append(C)
    S = [pilas[0]] * ne + pilas[:i_cut + 1] + zona_nudo
    A = [aire[0]] * ne + aire[:i_cut + 1] + [aire[min(i_cut + j, len(p) - 1)] for j in range(1, nn + 1)]
    P_ = np.vstack([p[0] - T[0] * 0.25 * np.arange(ne, 0, -1)[:, None], p[:i_cut + 1], p[i_cut + 1:i_cut + 1 + nn]])
    S, A = S[:len(P_)], A[:len(P_)]
    Tq, Uq, Wq = marcos(P_)
    for holg, lista in ((0.0, CUT), (HOLG, CUT_H)):
        vol = []
        for C, Ai in zip(S, A):
            Cd = ndimage.binary_dilation(C, iterations=int(round(holg / PX))) if holg else C
            vol.append(Cd | (Ai & ~ndimage.binary_dilation(~Ai, iterations=2) if False else Cd) | (Ai & ndimage.binary_dilation(Cd, iterations=int(0.6 / PX))))
        V = np.pad(np.array(vol, np.float32), ((1, 1), (1, 1), (1, 1)))
        V1 = ndimage.gaussian_filter(V, (3.0, 1.2, 1.2)); V2 = ndimage.gaussian_filter(V, (1.0, 1.2, 1.2))
        wv = np.ones(len(V)); m_ = len(V); wv[:ne + 6] = 0; wv[m_ - nn - 8:] = 0
        wv = ndimage.uniform_filter1d(wv, 7)[:, None, None]
        V = wv * V1 + (1 - wv) * V2     # suaviza la unión con el pecho, menos en las puntas
        vv, ff, _, _ = marching_cubes(V, 0.5)
        si, ui, wi = vv[:, 0] - 1, (vv[:, 1] - 1) * PX - VENT, (vv[:, 2] - 1) * PX - VENT
        si = np.clip(si, 0, len(P_) - 1); i0 = np.floor(si).astype(int); i1 = np.minimum(i0 + 1, len(P_) - 1); f = (si - i0)[:, None]
        lerp = lambda X: X[i0] * (1 - f) + X[i1] * f
        Pw = lerp(P_) + lerp(Uq) * ui[:, None] + lerp(Wq) * wi[:, None]
        mt = trimesh.Trimesh(Pw, ff, process=True); trimesh.repair.fix_normals(mt)
        if mt.volume < 0: mt.invert()
        Mm = man(mt); print(k, "cortador", "holgura" if holg else "", Mm.status(), round(Mm.volume(), 1), flush=True)
        lista.append(Mm)
print(json.dumps(info), flush=True)
CUTm = CUT[0] + CUT[1]; CUTh = CUT_H[0] + CUT_H[1]
A_ = SOL - CUTm; partes = sorted(A_.decompose(), key=lambda q: -q.volume())
sueltos = [q for q in partes[1:] if q.volume() > 0.05]
collar = SOL ^ CUTm
for q in sueltos: collar = collar + q
cp = sorted(collar.decompose(), key=lambda q: -q.volume())
print("collar piezas", [round(q.volume(), 1) for q in cp[:5]], "sueltos", [round(q.volume(), 1) for q in sueltos[:5]], flush=True)
cuerpo = CUE - CUTh; bp = sorted(cuerpo.decompose(), key=lambda q: -q.volume())
print("cuerpo piezas", [round(q.volume(), 2) for q in bp[:6]], flush=True)
tm(cp[0]).export(out / "collar.stl"); tm(bp[0]).export(out / "cuerpo_sin_collar.stl")
for i, q in enumerate(cp[1:3]): tm(q).export(out / f"collar_resto{i}.stl")
info["collar_mm3"] = round(cp[0].volume(), 1); info["collar_piezas"] = len([q for q in cp if q.volume() > 0.5])
json.dump(info, open(out / "collar.json", "w"), indent=1)
