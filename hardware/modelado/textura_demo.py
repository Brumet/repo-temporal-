"""
Prueba de calidad de superficie en parches: original vs subdivision suave (butterfly, interpola: conserva la
escultura y quita las facetas) vs subdivision + micro-textura procedimental (roca: grano + grietas finas;
hueso: poros; plumas: barbas finas siguiendo la direccion de la pluma).
Uso: python textura_demo.py "forma preliminar.stl" salida
"""
import sys
from pathlib import Path
import numpy as np, trimesh, pymeshlab

src, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
m = trimesh.load_mesh(src, process=True)
PARCHES = {"calavera": ((-28, 28), (-95, -40), (62, 118), "hueso"),
           "roca": ((35, 92), (-75, 5), (2, 40), "roca"),
           "plumas": ((-18, 18), (-52, -28), (212, 246), "pluma")}

# ---------- ruido 3D (gradiente, con hash) en numpy
_rng = np.random.default_rng(7); _perm = _rng.permutation(256); _perm = np.r_[_perm, _perm]
_grad = _rng.normal(size=(256, 3)); _grad /= np.linalg.norm(_grad, axis=1, keepdims=True)


def ruido(p):
    pi = np.floor(p).astype(int); pf = p - pi; w = pf * pf * pf * (pf * (pf * 6 - 15) + 10)
    tot = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = _perm[(_perm[(_perm[(pi[:, 0] + dx) & 255] + pi[:, 1] + dy) & 255] + pi[:, 2] + dz) & 255]
                g = (_grad[h] * (pf - [dx, dy, dz])).sum(1)
                wx = w[:, 0] if dx else 1 - w[:, 0]; wy = w[:, 1] if dy else 1 - w[:, 1]; wz = w[:, 2] if dz else 1 - w[:, 2]
                tot = tot + g * wx * wy * wz
    return tot


def fbm(p, oct=4):
    s, a, f = 0, 1, 1
    for _ in range(oct): s = s + a * ruido(p * f); a *= 0.5; f *= 2.0
    return s


def subdividir(t, n=2, alfa=0.75):
    """Teselación Phong: cada triángulo → 4; el punto medio de cada arista se curva según las normales de sus
    extremos (interpola: los vértices originales no se mueven, se quitan las facetas)."""
    V, F, N = t.vertices.copy(), t.faces.copy(), t.vertex_normals.copy()
    for _ in range(n):
        tt = trimesh.Trimesh(V, F, process=False)
        E = tt.edges_unique; FE = tt.faces_unique_edges
        a, b = V[E[:, 0]], V[E[:, 1]]; na, nb = N[E[:, 0]], N[E[:, 1]]; M = (a + b) / 2
        pa = M - ((M - a) * na).sum(1)[:, None] * na; pb = M - ((M - b) * nb).sum(1)[:, None] * nb
        Mp = (1 - alfa) * M + alfa * (pa + pb) / 2
        Nm = na + nb; Nm /= np.maximum(np.linalg.norm(Nm, axis=1, keepdims=True), 1e-12)
        o = len(V); e0, e1, e2 = FE[:, 0] + o, FE[:, 1] + o, FE[:, 2] + o
        F = np.vstack([np.c_[F[:, 0], e0, e2], np.c_[e0, F[:, 1], e1], np.c_[e2, e1, F[:, 2]], np.c_[e0, e1, e2]])
        V = np.vstack([V, Mp]); N = np.vstack([N, Nm])
    return trimesh.Trimesh(V, F, process=False)


def textura(t, tipo):
    v = t.vertices.copy(); n = t.vertex_normals
    if tipo == "roca":       # grano + grietas finas (ruido "ridged")
        d = 0.06 * fbm(v / 0.9) - 0.10 * np.clip(1 - np.abs(ruido(v / 3.5 + 11)) * 6, 0, 1) ** 3
    elif tipo == "hueso":    # poros pequeños + ondulación suave
        por = np.clip(ruido(v / 0.35 + 3) - 0.25, 0, None)
        d = 0.025 * fbm(v / 1.6) - 0.09 * por
    else:                    # barbas: surcos finos casi perpendiculares a la dirección de la pluma (hacia abajo)
        g = np.array([0, 0.25, -1.0]); g /= np.linalg.norm(g)
        tdir = g - n * (n @ g)[:, None]; tdir /= np.maximum(np.linalg.norm(tdir, axis=1, keepdims=True), 1e-9)
        b = np.cross(n, tdir)                                   # dirección de las barbas
        fase = (v @ np.array([0, 0, 1.0])) * 0 + (v * (0.55 * tdir + 0.83 * b)).sum(1) * 0 + (v @ g) / 0.30 + 0.4 * ruido(v / 1.5)
        d = -0.035 * (0.5 + 0.5 * np.cos(2 * np.pi * fase)) ** 3 + 0.01 * ruido(v / 0.5)
    return trimesh.Trimesh(v + n * d[:, None], t.faces, process=False)


for nom, (xr, yr, zr, tipo) in PARCHES.items():
    c = m.triangles_center
    sel = (c[:, 0] > xr[0]) & (c[:, 0] < xr[1]) & (c[:, 1] > yr[0]) & (c[:, 1] < yr[1]) & (c[:, 2] > zr[0]) & (c[:, 2] < zr[1])
    p = m.submesh([np.nonzero(sel)[0]], append=True)
    p.export(out / f"{nom}_0_original.stl")
    s = subdividir(p, 2); s.export(out / f"{nom}_1_suave.stl")
    textura(s, tipo).export(out / f"{nom}_2_textura.stl")
    print(nom, "caras", len(p.faces), "->", len(s.faces), flush=True)
