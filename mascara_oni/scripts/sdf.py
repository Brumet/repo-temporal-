"""Mini motor de campos de distancia (SDF) sobre una rejilla de vóxeles.

Cada primitiva se evalúa solo dentro de su caja envolvente para ahorrar
memoria y tiempo. Unidades: mm. La cara mira a -Y, +Z arriba.
"""
import numpy as np


# ---------- utilidades ----------
def normalize(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(u, up=(0, 0, 1)):
    """Base ortonormal cuyo eje X local es u (filas = ejes locales)."""
    u = normalize(u)
    w = np.cross(u, up)
    if np.linalg.norm(w) < 1e-6:
        w = np.cross(u, (0, 1, 0))
    w = normalize(w)
    v = np.cross(w, u)
    return np.array([u, w, v])  # x local, y local, z local


def bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# ---------- primitivas (reciben coordenadas locales a la caja) ----------
def _local(X, Y, Z, c, R):
    px, py, pz = X - c[0], Y - c[1], Z - c[2]
    if R is None:
        return px, py, pz
    return (px * R[0, 0] + py * R[0, 1] + pz * R[0, 2],
            px * R[1, 0] + py * R[1, 1] + pz * R[1, 2],
            px * R[2, 0] + py * R[2, 1] + pz * R[2, 2])


def ellipsoid(c, r, R=None):
    c = np.asarray(c, float); r = np.asarray(r, float)
    def f(X, Y, Z):
        x, y, z = _local(X, Y, Z, c, R)
        k0 = np.sqrt((x / r[0]) ** 2 + (y / r[1]) ** 2 + (z / r[2]) ** 2)
        k1 = np.sqrt((x / r[0] ** 2) ** 2 + (y / r[1] ** 2) ** 2 + (z / r[2] ** 2) ** 2)
        return k0 * (k0 - 1) / np.maximum(k1, 1e-9)
    ext = r.max() + 2
    return f, (c - ext, c + ext)


def rbox(c, h, rad=1.0, R=None):
    c = np.asarray(c, float); h = np.asarray(h, float)
    def f(X, Y, Z):
        x, y, z = _local(X, Y, Z, c, R)
        qx, qy, qz = np.abs(x) - h[0] + rad, np.abs(y) - h[1] + rad, np.abs(z) - h[2] + rad
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
        return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - rad
    ext = np.linalg.norm(h) + 2
    return f, (c - ext, c + ext)


def round_cone(a, b, r1, r2):
    """Cono redondeado entre a (radio r1) y b (radio r2) — fórmula de I. Quilez."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    ba = b - a; l2 = ba @ ba; rr = r1 - r2; a2 = l2 - rr * rr; il2 = 1.0 / l2
    def f(X, Y, Z):
        pax, pay, paz = X - a[0], Y - a[1], Z - a[2]
        y = pax * ba[0] + pay * ba[1] + paz * ba[2]
        z = y - l2
        qx, qy, qz = pax * l2 - ba[0] * y, pay * l2 - ba[1] * y, paz * l2 - ba[2] * y
        x2 = qx * qx + qy * qy + qz * qz
        y2 = y * y * l2; z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d_tip = np.sqrt(x2 + z2) * il2 - r2
        d_base = np.sqrt(x2 + y2) * il2 - r1
        d_side = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        return np.where(np.sign(z) * a2 * z2 > k, d_tip,
                        np.where(np.sign(y) * a2 * y2 < k, d_base, d_side))
    m = max(r1, r2) + 2
    return f, (np.minimum(a, b) - m, np.maximum(a, b) + m)


def horn(p0, p1, p2, p3, r_base, r_tip, n=40, power=1.3):
    """Cuerno: cadena de conos redondeados a lo largo de una Bézier cúbica."""
    pts = bezier(p0, p1, p2, p3, n)
    t = np.linspace(0, 1, n)
    rad = r_tip + (r_base - r_tip) * (1 - t) ** power
    segs = [round_cone(pts[i], pts[i + 1], rad[i], rad[i + 1]) for i in range(n - 1)]
    lo = np.min([s[1][0] for s in segs], axis=0); hi = np.max([s[1][1] for s in segs], axis=0)
    return segs, (lo, hi), pts, rad


# ---------- rejilla ----------
class Grid:
    def __init__(self, lo, hi, step):
        self.lo = np.asarray(lo, float); self.step = step
        self.n = np.ceil((np.asarray(hi, float) - self.lo) / step).astype(int) + 1
        self.D = np.full(self.n, 1e3, np.float32)
        print("rejilla", self.n, f"{self.D.size/1e6:.1f} M vóxeles")

    def _region(self, bbox, pad):
        lo = np.floor((np.asarray(bbox[0]) - pad - self.lo) / self.step).astype(int)
        hi = np.ceil((np.asarray(bbox[1]) + pad - self.lo) / self.step).astype(int) + 1
        lo = np.clip(lo, 0, self.n); hi = np.clip(hi, 0, self.n)
        if np.any(hi <= lo):
            return None
        sl = tuple(slice(l, h) for l, h in zip(lo, hi))
        ax = [self.lo[i] + self.step * np.arange(lo[i], hi[i]) for i in range(3)]
        X = ax[0][:, None, None]; Y = ax[1][None, :, None]; Z = ax[2][None, None, :]
        return sl, X, Y, Z

    def _eval(self, prim, X, Y, Z):
        if isinstance(prim, list):  # lista de segmentos (cuerno)
            out = None
            for f, _ in prim:
                d = f(X, Y, Z)
                out = d if out is None else np.minimum(out, d)
            return out
        return prim(X, Y, Z)

    def add(self, item, k=0.0):
        prim, bbox = item[0], item[1]
        r = self._region(bbox, k + 2)
        if r is None: return
        sl, X, Y, Z = r
        self.D[sl] = smin(self.D[sl], self._eval(prim, X, Y, Z), k)

    def sub(self, item, k=0.0):
        prim, bbox = item[0], item[1]
        r = self._region(bbox, k + 2)
        if r is None: return
        sl, X, Y, Z = r
        self.D[sl] = smax(self.D[sl], -self._eval(prim, X, Y, Z), k)

    def axes(self):
        return [self.lo[i] + self.step * np.arange(self.n[i]) for i in range(3)]
