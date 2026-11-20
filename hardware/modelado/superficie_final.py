"""
Superficie final de las piezas (aprobado por Bru): roca basalto v3b + poros de hueso + barbas orientadas v2.

Paso A (una vez, sobre el modelo entero cuervo_reparado.stl → campo.npz):
  banda de detalle h, dirección de las barbas (tensor de estructura), coherencia, energía y curvatura por vértice,
  e impulsos de Gabor en una rejilla 3D fija cerca de la superficie (los mismos para todas las piezas:
  las barbas siguen continuas a través de las costuras).
Paso B (por pieza): solo la superficie ORIGINAL cambia (encastres, huecos, tapa, USB intactos).
  realce suave de las barbas existentes → refinamiento rojo-verde (N1 en todo; N2 donde hay barbas y en la roca;
  N3 en la roca) con Phong → desplazamientos: roca (z < 39), hueso (calavera), barbas (z > 125, donde hay barbas).
Uso: python superficie_final.py cuervo_reparado.stl salida pieza1.stl [pieza2.stl ...]
"""
import sys, time
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix, diags
sys.path.insert(0, str(Path(__file__).parent))
from textura_demo import ruido, fbm  # noqa: E402
from superficie_v3 import roca_d, worley  # noqa: E402
from mejorar_superficie import refinar, normales  # noqa: E402

LAM, AMP, KERN, REALCE, CELDA = 0.45, 0.035, 0.9, 0.5, 0.5
Z_BARBAS = 125.0
ref_f, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
piezas = sys.argv[3:]
T0 = time.time(); log = lambda *a: print(f"[{time.time() - T0:5.0f} s]", *a, flush=True)


def W_vecinos(nV, F):
    t = trimesh.Trimesh(np.zeros((nV, 3)), F, process=False); E = t.edges_unique
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nV, nV)).tocsr()
    return diags(1 / np.maximum(np.asarray(A.sum(1)).ravel(), 1)) @ A


def suav(X, W, it):
    for _ in range(it): X = 0.5 * X + 0.5 * (W @ X)
    return X


# ---------------- Paso A: campo global
campo_f = out / "campo.npz"
ref = trimesh.load_mesh(ref_f, process=True); VR = ref.vertices; NR = ref.vertex_normals; TR = cKDTree(VR)
if campo_f.exists():
    C = dict(np.load(campo_f)); log("campo cargado")
else:
    WR = W_vecinos(len(VR), ref.faces)
    s1, s3, s12 = suav(VR, WR, 1), suav(VR, WR, 3), suav(VR, WR, 12)
    h = ((s1 - s12) * NR).sum(1); curv = np.abs(((VR - s3) * NR).sum(1))
    a = np.cross(NR, np.where(np.abs(NR[:, :1]) < 0.9, [[1.0, 0, 0]], [[0, 1.0, 0]])); a /= np.linalg.norm(a, axis=1, keepdims=True)
    b = np.cross(NR, a); g = np.zeros_like(VR)
    for i0 in range(0, len(VR), 400000):
        sl = slice(i0, i0 + 400000); _, J = TR.query(VR[sl], k=14, workers=-1)
        D = VR[J] - VR[sl][:, None, :]; u = (D * a[sl][:, None]).sum(2); v = (D * b[sl][:, None]).sum(2); dh = h[J] - h[sl][:, None]
        Suu, Suv, Svv, Suh, Svh = (u * u).sum(1), (u * v).sum(1), (v * v).sum(1), (u * dh).sum(1), (v * dh).sum(1)
        det = Suu * Svv - Suv ** 2 + 1e-12
        g[sl] = ((Svv * Suh - Suv * Svh) / det)[:, None] * a[sl] + ((Suu * Svh - Suv * Suh) / det)[:, None] * b[sl]
    Jt = (g[:, :, None] * g[:, None, :]).reshape(-1, 9)
    Jm = np.zeros_like(Jt)
    for i0 in range(0, len(VR), 200000):
        sl = slice(i0, i0 + 200000); _, K = TR.query(VR[sl], k=96, workers=-1); Jm[sl] = Jt[K].mean(1)
    w, e = np.linalg.eigh(Jm.reshape(-1, 3, 3))
    e1 = e[:, :, 2]; e1 -= NR * (e1 * NR).sum(1)[:, None]; e1 /= np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-9)
    coh = (w[:, 2] - w[:, 1]) / (w[:, 2] + w[:, 1] + 1e-12); en = np.sqrt(np.maximum(w[:, 2], 0))
    # impulsos de Gabor: rejilla 3D con jitter, solo cerca de la superficie
    lo, hi = VR.min(0) - 1, VR.max(0) + 1; rng = np.random.default_rng(5)
    P = []
    for z0 in np.arange(lo[2], hi[2], CELDA * 40):
        g3 = np.stack(np.meshgrid(np.arange(lo[0], hi[0], CELDA), np.arange(lo[1], hi[1], CELDA), np.arange(z0, min(z0 + CELDA * 40, hi[2]), CELDA), indexing="ij"), -1).reshape(-1, 3)
        g3 = g3 + rng.uniform(0, CELDA, g3.shape)
        dd, _ = TR.query(g3, distance_upper_bound=0.6, workers=-1); P.append(g3[np.isfinite(dd)])
    P = np.vstack(P); _, jp = TR.query(P, workers=-1)
    C = dict(h=h, e1=e1, coh=coh, en=en, curv=curv, P=P, PD=e1[jp], PW=rng.choice([-1.0, 1.0], len(P)) * rng.uniform(0.6, 1.0, len(P)),
             PF=rng.uniform(0, 2 * np.pi, len(P)))
    np.savez(campo_f, **C); log("campo calculado:", len(VR), "vértices,", len(P), "impulsos")
TP = cKDTree(C["P"])
CUERO = np.load(Path(ref_f).parent / "cuero" / "cuero_vertices.npy").astype(float)   # A, B, C, D, F (marcado por Bru)


def cuero_d(V):
    """Grano de cuero: celdas como granos (surcos finos entre ellas) + poros + arrugas muy suaves."""
    f1, _, _ = worley(V, 0.45, 7)
    surco = -0.035 * np.clip((f1 / 0.45 - 0.42) / 0.35, 0, 1) ** 2
    f1b, idb, _ = worley(V, 0.30, 8); poro = -0.022 * np.clip(1 - f1b / 0.06, 0, 1) * ((idb % 100) < 35)
    return surco + poro + 0.018 * fbm(V / 2.5, 2)


def peso_barbas(j, z):
    # SOLO donde la escultura ya trae barbas (versión aprobada en el ala); plumas lisas (espalda) quedan con su relieve
    w = (np.clip((C["coh"][j] - 0.35) / 0.3, 0, 1) * np.clip((C["en"][j] - 0.04) / 0.06, 0, 1)
         * np.clip(1 - (C["curv"][j] - 0.03) / 0.05, 0, 1))
    return w * np.clip((z - Z_BARBAS) / 4.0, 0, 1)


def gabor(V):
    G = np.zeros(len(V))
    for i0 in range(0, len(V), 500000):
        sl = slice(i0, i0 + 500000)
        dist, idx = TP.query(V[sl], k=24, distance_upper_bound=KERN * 1.6, workers=-1)
        ok = idx < len(C["P"]); idx = np.where(ok, idx, 0)
        d = V[sl][:, None, :] - C["P"][idx]
        val = C["PW"][idx] * np.exp(-np.pi * (d * d).sum(2) / KERN ** 2) * np.cos(2 * np.pi * (d * C["PD"][idx]).sum(2) / LAM + C["PF"][idx])
        G[sl] = (val * ok).sum(1)
    return G / 0.55          # normalización fija (≈ desviación típica medida en el ala): igual en todas las piezas


def suave(z, a, b): return np.clip((z - a) / (b - a), 0, 1)


PA, PB = np.array([6.6, -89.1, 240.6]), np.array([3.0, -62.0, 272.0])   # punta → base del pico


def peso_pico(V):
    """1 dentro del pico (con su banda y nariz, tal como está esculpido), 0 fuera; transición suave."""
    u = (PB - PA) / np.linalg.norm(PB - PA); t = (V - PA) @ u; r = np.linalg.norm(V - PA - np.outer(t, u), axis=1)
    return np.clip((24.0 - t) / 2.0, 0, 1) * np.clip((t + 3) / 1.0, 0, 1) * np.clip((12.5 - r) / 1.5, 0, 1)


for f in piezas:
    nombre = Path(f).stem; t = trimesh.load_mesh(f, process=True); V, F = t.vertices.copy(), t.faces.copy()
    dist, j = TR.query(V, workers=-1); orig = dist < 1e-3
    log(nombre, "caras", len(F), "| original %", round(100 * orig.mean()))
    # realce suave de las barbas existentes (solo superficie original, zona de plumas)
    sin_barbas = nombre.startswith("collar")          # pieza del collar: cuerdas (cuero) + dije (metal), sin barbas
    wz = suave(V[:, 2], Z_BARBAS, Z_BARBAS + 4) * orig * (1 - peso_pico(V)) * (1 - CUERO[j]) * (not sin_barbas)
    V = V + (REALCE * np.clip(C["h"][j], -0.2, 0.2) * wz)[:, None] * NR[j]
    marca = orig[F].all(1)
    V, F, orig = refinar(V, F, orig, marca); log("  N1", len(F))
    _, j = TR.query(V, workers=-1); z = V[:, 2]
    wb = peso_barbas(j, z) * orig * (1 - peso_pico(V)) * (1 - CUERO[j]) * (not sin_barbas)
    cz = V[F].mean(1)[:, 2]
    marca2 = orig[F].all(1) & ((cz < 40.0) | (wb[F].max(1) > 0.02) | (CUERO[j][F].max(1) > 0.5))
    V, F, orig = refinar(V, F, orig, marca2); log("  N2", len(F))
    cz = V[F].mean(1)[:, 2]; marca3 = orig[F].all(1) & (cz < 39.5)
    if marca3.any(): V, F, orig = refinar(V, F, orig, marca3); log("  N3 roca", len(F))
    N = normales(V, F); _, j = TR.query(V, workers=-1); x, y, z = V[:, 0], V[:, 1], V[:, 2]
    d = np.zeros(len(V))
    # roca
    wr = (1 - suave(z, 37.0, 40.0)) * orig; r = wr > 0
    if r.any():
        dr = np.zeros(len(V)); dr[r] = roca_d(V[r], N[r])
        Wv = W_vecinos(len(V), F); dr = suav(dr, Wv, 2); d += wr * dr
    # hueso
    wh = suave(z, 39.0, 42.0) * (1 - suave(z, 120.0, 128.0)) * (1 - suave(y, 40.0, 48.0)) * orig; hsel = wh > 0
    if hsel.any():
        por = np.clip(ruido(V[hsel] / 0.5 + 3) - 0.25, 0, None)
        d[hsel] += wh[hsel] * (0.025 * fbm(V[hsel] / 1.6) - 0.08 * por)
    # barbas
    wp = peso_pico(V) * orig
    wc = CUERO[j] * orig
    if wc.any():
        Wc = W_vecinos(len(V), F); wc = np.clip(suav(wc, Wc, 3) * 1.4, 0, 1) * orig      # borde suave del cuero
        csel = wc > 0
        d[csel] += wc[csel] * cuero_d(V[csel])
    wb = peso_barbas(j, z) * orig * (1 - wp) * (1 - wc) * (not sin_barbas); bsel = wb > 0
    psel = wp > 0
    if psel.any(): d[psel] += wp[psel] * (0.010 * fbm(V[psel] / 0.6, 3))     # queratina: grano fino, sin líneas
    if bsel.any():
        G = gabor(V[bsel]); d[bsel] += -AMP * np.clip(G - 0.3, 0, 2.5) ** 1.3 * wb[bsel]
    V = V + N * d[:, None]
    r = trimesh.Trimesh(V, F, process=False)
    log("  ->", nombre, len(F), "caras | barbas en", int(bsel.sum()), "vértices | cerrada", r.is_watertight)
    r.export(out / f"{nombre}.stl")
