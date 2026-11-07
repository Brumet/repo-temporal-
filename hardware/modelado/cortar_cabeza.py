"""
Corta la cabeza siguiendo el canto real del collar (superficie curva h = h_borde(θ),
medida con borde_collar.py) y genera la unión para pegarla.

  h = distancia con signo al plano (positivo hacia la cabeza), d = profundidad desde la superficie.
  - Franja de refuerzo: pared de 5 mm en h ∈ [-REF, REF] (en vez de 3 mm).
  - Labio en el cuerpo: d ∈ [SKIN+HOLG, 5] y h ∈ [0, LABIO] → entra por dentro de la cabeza.
  - Cabeza: en h ∈ [0, LABIO+0,2] queda solo la piel exterior d ≤ SKIN (ahí asienta el labio).
  El labio sigue la forma irregular del cuello: la cabeza solo entra en una posición.

Las profundidades se calculan en vóxeles de VOX mm solo alrededor del cuello.
Uso: python cortar_cabeza.py cuervo_reparado.stl cuervo_hueco.stl borde_collar.json carpeta_salida
"""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

REF = 12.0         # franja con pared de 5 mm a cada lado del corte
PARED_UNION = 5.0
SKIN = 2.5         # piel exterior de la cabeza sobre el labio
HOLG = 0.15        # holgura para el pegamento
LABIO = 5.0        # alto del labio
VOX = 0.25

src_solid, src_hueco, src_borde, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
B = json.load(open(src_borde))
n, ex, ey, C0 = np.array(B["n"]), np.array(B["ex"]), np.array(B["ey"]), np.array(B["centro"])
TH, HB = np.array(B["theta"]), np.array(B["h_borde"])


def h_rel(P):
    """Altura sobre la superficie de corte (positivo hacia la cabeza)."""
    d = P - C0; th = np.arctan2(d @ ey, d @ ex) % (2 * np.pi)
    return d @ n - np.interp(th, TH, HB, period=2 * np.pi)
solid_t = trimesh.load_mesh(src_solid, process=True)
hueco_t = trimesh.load_mesh(src_hueco, process=True)
man = lambda t: mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
SOL, HUE = man(solid_t), man(hueco_t)
print("cargado", SOL.status(), HUE.status(), f"{time.time()-t0:.0f} s", flush=True)

# ——— Profundidad en una caja alrededor del cuello ———
h_v = h_rel(solid_t.vertices)
zona = solid_t.vertices[np.abs(h_v) < REF + 8]
lo, hi = zona.min(0) - 2, zona.max(0) + 2
nx, ny = int(np.ceil((hi[0] - lo[0]) / VOX)), int(np.ceil((hi[1] - lo[1]) / VOX))
zs = np.arange(lo[2] + VOX / 2, hi[2], VOX)
vol = np.zeros((len(zs), ny, nx), bool)
secs = solid_t.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs.tolist())
for k, s in enumerate(secs):
    if s is None:
        continue
    T = s.metadata["to_3D"]; acc = np.zeros((ny, nx), bool)
    for loop in s.discrete:
        if len(loop) < 3:
            continue
        p3 = trimesh.transform_points(np.column_stack([loop[:, :2], np.zeros(len(loop))]), T)
        img = Image.new("1", (nx, ny), 0)
        ImageDraw.Draw(img).polygon([((x - lo[0]) / VOX, (y - lo[1]) / VOX) for x, y in p3[:, :2]], fill=1)
        acc ^= np.array(img)
    vol[k] = acc
print(f"vóxeles {vol.shape} · {time.time()-t0:.0f} s", flush=True)
vol = np.pad(vol, 2)
prof = ndimage.distance_transform_edt(vol, sampling=VOX).astype(np.float32)


def nucleo(dmin):
    """Malla cerrada de los puntos a más de dmin mm de la superficie (dentro de la caja)."""
    campo = ndimage.gaussian_filter(prof, 0.6)
    v, f, _, _ = measure.marching_cubes(campo, dmin, spacing=(VOX, VOX, VOX))
    v = v[:, ::-1] + (lo - 2 * VOX + [0, 0, VOX / 2])
    t = trimesh.Trimesh(v, f[:, ::-1], process=True)
    trimesh.repair.fix_normals(t)
    if t.volume < 0:
        t.invert()
    return man(t)


N_skin, N_lab, N_5 = nucleo(SKIN), nucleo(SKIN + HOLG), nucleo(PARED_UNION)
print("núcleos", N_skin.status(), N_lab.status(), N_5.status(), f"{time.time()-t0:.0f} s", flush=True)


def franja(a, b, R=170.0, NT=360, NR=60):
    """Sólido entre la superficie de corte desplazada a y b (h hacia la cabeza), hasta radio R."""
    hb = np.interp(np.linspace(0, 2 * np.pi, NT, endpoint=False), TH, HB, period=2 * np.pi)
    th = np.linspace(0, 2 * np.pi, NT, endpoint=False)
    rs = np.linspace(0, R, NR + 1)[1:]
    media = HB.mean()
    def capa(off):
        s_ = np.clip(rs / 8.0, 0, 1)[None, :]                 # cerca del eje: altura media (evita el pliegue)
        hh = (hb[:, None] * s_ + media * (1 - s_)) + off
        P = (C0 + rs[None, :, None] * (np.cos(th)[:, None, None] * ex + np.sin(th)[:, None, None] * ey)
             + hh[..., None] * n)
        cen = C0 + (media + off) * n
        return np.vstack([cen[None], P.reshape(-1, 3)])
    V = np.vstack([capa(a), capa(b)]); off = NT * NR + 1
    idx = lambda i, j: 1 + (i % NT) * NR + j
    F = []
    for i in range(NT):
        F.append([0, idx(i + 1, 0), idx(i, 0)]); F.append([off, off + idx(i, 0), off + idx(i + 1, 0)])
        for j in range(NR - 1):
            a0, a1, b0, b1 = idx(i, j), idx(i + 1, j), idx(i, j + 1), idx(i + 1, j + 1)
            F += [[a0, a1, b1], [a0, b1, b0], [off + a0, off + b1, off + a1], [off + a0, off + b0, off + b1]]
        e0, e1 = idx(i, NR - 1), idx(i + 1, NR - 1)
        F += [[e0, e1, off + e1], [e0, off + e1, off + e0]]
    t = trimesh.Trimesh(V, np.array(F), process=True)
    trimesh.repair.fix_normals(t)
    if t.volume < 0:
        t.invert()
    return man(t)


arriba = franja(0, 500)          # la cabeza está a < 70 mm del eje: R=170 la cubre entera
pared5 = SOL - N_5
cabeza = (HUE ^ arriba) + (pared5 ^ franja(0, REF))
cabeza = cabeza - (N_skin ^ franja(-1, LABIO + 0.2))
cuerpo = (HUE - arriba) + (pared5 ^ franja(-REF, 0)) + ((N_lab - N_5) ^ franja(0, LABIO))
print("booleanas", f"{time.time()-t0:.0f} s", flush=True)


def guarda(mm, nombre):
    me = mm.to_mesh()
    trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=False).export(out / nombre)


guarda(cabeza, "cabeza.stl"); guarda(cuerpo, "cuerpo.stl")
bb = lambda mm: np.round(np.array(mm.bounding_box()), 1).tolist()
info = {"corte": "curvo, canto del collar (borde_collar.json)", "pared_union_mm": PARED_UNION, "piel_cabeza_mm": SKIN, "holgura_mm": HOLG, "labio_mm": LABIO,
        "cabeza_cm3": round(cabeza.volume() / 1000, 1), "cuerpo_cm3": round(cuerpo.volume() / 1000, 1),
        "cabeza_caja_mm": bb(cabeza), "cuerpo_caja_mm": bb(cuerpo),
        "piezas_cabeza_cm3": sorted([round(p.volume() / 1000, 2) for p in cabeza.decompose()], reverse=True)[:6],
        "piezas_cuerpo_cm3": sorted([round(p.volume() / 1000, 2) for p in cuerpo.decompose()], reverse=True)[:6]}
(out / "corte.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(info, indent=2, ensure_ascii=False), f"\n{time.time()-t0:.0f} s")
