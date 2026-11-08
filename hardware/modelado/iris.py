"""
Iris procedimental para el interior del inserto (estilo fibras + collarete + pupila).

Devuelve el grosor extra (mm, >= 0) que se suma por DENTRO de la cúpula, en coordenadas del
plano del ojo (x, y) en mm. Pensado para resina con luz detrás: cada borde de fibra refracta
la luz y dibuja una línea; la pupila es un disco plano más grueso con borde nítido (se puede
pintar negro por dentro).

Medidas imprimibles (Jupiter 2, ~50 µm XY): fibras de ~0,16 mm de base, 0,12-0,2 mm de alto.
"""
import numpy as np

CEN = np.array([0.45, 0.45])  # centro de la pupila del iris tallado original (ojo izquierdo)
R_PUP, R_COL, R_IRIS = 1.30, 2.05, 3.30
H_PUP, H_COL, H_FIB_EXT, H_FIB_INT, H_LIMBO = 0.60, 0.38, 0.20, 0.13, 0.22
W_FIB, N_EXT, N_INT, N_PICOS = 0.085, 120, 80, 14


def _prof(u):  # perfil redondeado de una cresta: 1 en el centro, 0 en |u|>=1
    u = np.clip(np.abs(u), 0, 1); return (1 - u * u) ** 1.5


def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def grosor(px, py, espejo=False, semilla=7, estilo="griego"):
    if estilo == "griego": return griego(px, py, espejo)
    return fibras_(px, py, espejo, semilla)


def fibras_(px, py, espejo=False, semilla=7):
    rng = np.random.default_rng(semilla)
    if espejo: px = -px
    dx, dy = px - CEN[0], py - CEN[1]
    r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    h = np.zeros_like(r)
    # collarete ondulado
    a = rng.uniform(0, 2 * np.pi, 4)
    rc = lambda t: R_COL + 0.13 * np.sin(5 * t + a[0]) + 0.08 * np.sin(9 * t + a[1]) + 0.04 * np.sin(17 * t + a[2])
    def fibras(n, r0, r1, alto, k_amp):
        out = np.zeros_like(r); zona = (r > r0 - 0.1) & (r < r1 + 0.1); rz, tz = r[zona], th[zona]
        acc = np.zeros_like(rz)
        for i in range(n):
            t0 = 2 * np.pi * (i + rng.uniform(-0.35, 0.35)) / n
            A, k, ph, giro = rng.uniform(0.2, 1.0) * k_amp, rng.uniform(2.0, 4.0), rng.uniform(0, 2 * np.pi), rng.uniform(-0.04, 0.04)
            a0 = r0 + rng.uniform(0, 0.25) * (r1 - r0); a1 = r1 - rng.uniform(0, 0.2) * (r1 - r0)
            ti = t0 + giro * (rz - r0) + A * np.sin(k * rz + ph)
            dth = (tz - ti + np.pi) % (2 * np.pi) - np.pi
            w = W_FIB * rng.uniform(0.8, 1.2)
            v = alto * rng.uniform(0.75, 1.0) * _prof(dth * rz / w) * _ss(a0, a0 + 0.15, rz) * (1 - _ss(a1 - 0.15, a1, rz))
            acc = np.maximum(acc, v)
        out[zona] = acc; return out
    rcol = rc(th)
    h = np.maximum(h, fibras(N_EXT, R_COL, R_IRIS - 0.05, H_FIB_EXT, 0.045) * _ss(rcol - 0.05, rcol + 0.1, r))
    h = np.maximum(h, fibras(N_INT, R_PUP, R_COL + 0.1, H_FIB_INT, 0.03) * (1 - _ss(rcol - 0.1, rcol + 0.05, r)))
    # collarete con grumos y picos hacia afuera
    grumo = 1 + 0.25 * np.sin(23 * th + a[3]) * np.sin(11 * th)
    h = np.maximum(h, H_COL * grumo * _prof((r - rcol) / 0.2))
    for t0 in rng.uniform(0, 2 * np.pi, N_PICOS):
        largo = rng.uniform(0.45, 0.9); dth = (th - t0 + np.pi) % (2 * np.pi) - np.pi
        s = np.clip((r - rc(t0)) / largo, 0, 1)
        anch = 0.16 * (1 - s) + 0.05
        v = H_COL * 0.9 * (1 - 0.7 * s) * _prof(dth * r / anch) * (r > rc(t0) - 0.1) * (s < 1)
        h = np.maximum(h, v)
    # limbo (borde del iris) y pupila
    h = np.maximum(h, H_LIMBO * _prof((r - R_IRIS) / 0.18))
    h = np.maximum(h, H_PUP * (1 - _ss(R_PUP - 0.08, R_PUP, r)))
    return h


def griego(px, py, espejo=False, n_estrias=28):
    """Estilo escultura clásica: iris en cono suave con borde inciso nítido, pupila 'taladrada'
    en cuenco y un punto de brillo; estrías radiales muy suaves. Rasgos >= 0,3 mm."""
    if espejo: px = -px
    dx, dy = px - CEN[0], py - CEN[1]
    r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    u = np.clip((r - R_PUP) / (R_IRIS - R_PUP), 0, 1)
    iris_ = (0.15 + 0.30 * (1 - u)) * (1 - _ss(R_IRIS - 0.06, R_IRIS + 0.04, r))
    estr = 0.022 * (0.5 + 0.5 * np.cos(n_estrias * th + 0.9 * np.sin(3 * th) + 0.5 * np.sin(7 * th + 1))) * _ss(R_PUP + 0.15, R_PUP + 0.5, r) * (1 - _ss(R_IRIS - 0.5, R_IRIS - 0.15, r))
    cuenco = 0.45 * (r / R_PUP) ** 2
    pupila = _ss(R_PUP - 0.06, R_PUP + 0.02, r)
    h = pupila * (iris_ + estr) + (1 - pupila) * cuenco
    b = np.hypot(dx + 0.38, dy - 0.42)
    h = np.maximum(h, 0.40 * _prof(b / 0.32) * (r < R_PUP))
    return h
