"""
Mejora de superficie de las piezas finales (opción 1).

- Solo la superficie ORIGINAL de la escultura (vértices que coinciden con cuervo_reparado.stl) se refina: el hueco
  interior, cortes, encastres, tapa, USB, casquillos, etc. no se tocan (las piezas siguen encajando igual).
- Refinamiento rojo-verde (conforme, sin grietas): nivel 1 en toda la superficie original, nivel 2 en la roca.
  Puntos medios con teselación Phong (curva según las normales; se quitan las facetas). En aristas vivas
  (normales a > 35°) el punto medio queda recto: no se redondean los cantos.
- Micro-textura (desplazamiento por la normal, función de la posición → continua entre piezas):
  roca (z < 39): grano + grietas finas; calavera (z 40–125, y < 45): poros de hueso. Nada en plumas/cuero.
Uso: python mejorar_superficie.py cuervo_reparado.stl salida pieza1.stl [pieza2.stl ...]
"""
import sys, time
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import ruido, fbm  # noqa: E402

ALFA, ANG_VIVO = 0.75, np.cos(np.radians(35))
if __name__ == "__main__":
    ref_f, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    piezas = sys.argv[3:]
    ref = trimesh.load_mesh(ref_f, process=True); TREF = cKDTree(ref.vertices)
else:
    piezas = []


def normales(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])      # ponderadas por área
    N = np.zeros_like(V)
    for k in range(3): np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def refinar(V, F, orig, marca):
    """Rojo-verde: caras 'marca' se parten en 4; vecinas con 1 arista partida en 2 (sin T-juntas)."""
    t = trimesh.Trimesh(V, F, process=False); E = t.edges_unique; FE = t.faces_unique_edges
    parte = np.zeros(len(E), bool); parte[FE[marca].ravel()] = True
    while True:                                   # cierre: 2 aristas partidas → partir las 3
        c = parte[FE].sum(1); dos = c == 2
        if not dos.any(): break
        parte[FE[dos].ravel()] = True
    N = normales(V, F)
    e = np.nonzero(parte)[0]; a, b = E[e, 0], E[e, 1]
    M = (V[a] + V[b]) / 2
    ok = orig[a] & orig[b] & ((N[a] * N[b]).sum(1) > ANG_VIVO)
    pa = M - ((M - V[a]) * N[a]).sum(1)[:, None] * N[a]; pb = M - ((M - V[b]) * N[b]).sum(1)[:, None] * N[b]
    Mp = np.where(ok[:, None], (1 - ALFA) * M + ALFA * (pa + pb) / 2, M)
    idx = np.full(len(E), -1); idx[e] = len(V) + np.arange(len(e))
    V2 = np.vstack([V, Mp]); orig2 = np.r_[orig, ok]
    c = parte[FE].sum(1); m0, m1, m2 = idx[FE[:, 0]], idx[FE[:, 1]], idx[FE[:, 2]]
    A, B, C = F[:, 0], F[:, 1], F[:, 2]
    nuevas = [F[c == 0]]
    s = c == 3
    nuevas += [np.c_[A, m0, m2][s], np.c_[m0, B, m1][s], np.c_[m2, m1, C][s], np.c_[m0, m1, m2][s]]
    s = (c == 1) & (m0 >= 0); nuevas += [np.c_[A, m0, C][s], np.c_[m0, B, C][s]]
    s = (c == 1) & (m1 >= 0); nuevas += [np.c_[A, B, m1][s], np.c_[A, m1, C][s]]
    s = (c == 1) & (m2 >= 0); nuevas += [np.c_[A, B, m2][s], np.c_[B, C, m2][s]]
    return V2, np.vstack(nuevas), orig2


def suave(z, a, b): return np.clip((z - a) / (b - a), 0, 1)


def textura(V, N, orig):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    w_roca = 1 - suave(z, 37.0, 40.0)
    w_hueso = suave(z, 39.0, 42.0) * (1 - suave(z, 120.0, 128.0)) * (1 - suave(y, 40.0, 48.0))
    d = np.zeros(len(V))
    r = w_roca > 0
    d[r] = w_roca[r] * (0.06 * fbm(V[r] / 0.9) - 0.10 * np.clip(1 - np.abs(ruido(V[r] / 3.5 + 11)) * 6, 0, 1) ** 3)
    h = w_hueso > 0
    por = np.clip(ruido(V[h] / 0.5 + 3) - 0.25, 0, None)
    d[h] = w_hueso[h] * (0.025 * fbm(V[h] / 1.6) - 0.08 * por)
    d[~orig] = 0
    return V + N * d[:, None]


for f in piezas:
    t0 = time.time(); nombre = Path(f).stem
    t = trimesh.load_mesh(f, process=True); V, F = t.vertices.copy(), t.faces.copy()
    dist, _ = TREF.query(V, workers=-1); orig = dist < 1e-3
    marca = orig[F].all(1)
    print(nombre, "caras", len(F), "superficie original %", round(100 * marca.mean()), flush=True)
    V, F, orig = refinar(V, F, orig, marca)                                  # nivel 1
    cz = V[F].mean(1)[:, 2]
    marca2 = orig[F].all(1) & (cz < 40.0)                                   # nivel 2: roca
    if marca2.any(): V, F, orig = refinar(V, F, orig, marca2)
    N = normales(V, F); V = textura(V, N, orig)
    r = trimesh.Trimesh(V, F, process=False)
    print("  ->", len(F), "caras | cerrada", r.is_watertight, "| %.0f s" % (time.time() - t0), flush=True)
    r.export(out / f"{nombre}.stl")
