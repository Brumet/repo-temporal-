"""Exportación: STL por color, 3MF para Bambu Studio, vistas previas PNG y comprobaciones."""
import math
import os
import uuid
import zipfile

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon
from shapely import affinity
from shapely.ops import unary_union
import manifold3d as mf

import fenix as F

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida")


# ---------------------------------------------------------------- vista 2D
def _patch(g, **kw):
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    verts, codes = [], []
    for p in polys:
        if not isinstance(p, Polygon) or p.is_empty:
            continue
        for ring in [p.exterior] + list(p.interiors):
            xy = np.asarray(ring.coords)
            verts += xy.tolist()
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
    if not verts:
        return None
    return PathPatch(MPath(verts, codes), **kw)


def vista_plana(piezas, ruta, juntas=None, titulo=""):
    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    for p in piezas:
        regs = p.regiones()
        huella = unary_union(p.huella_extra) if p.huella_extra else Polygon()
        for color, g, h in sorted(regs, key=lambda r: r[2]):
            g = g.difference(huella)
            pa = _patch(g, facecolor=F.RGB[color], edgecolor="#00000055", lw=0.3)
            if pa:
                ax.add_patch(pa)
        for g in p.huella_extra:
            pa = _patch(g, facecolor=F.RGB["rojo"], edgecolor="#00000088", lw=0.3)
            if pa:
                ax.add_patch(pa)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.grid(True, lw=0.3, alpha=0.4)
    ax.set_title(titulo)
    fig.savefig(ruta, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- render 3D sencillo (sombreado)
def render(solid_por_color, ruta, elev=55, azim=-90, size=(8, 8)):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=size, dpi=170)
    ax = fig.add_subplot(111, projection="3d")
    luz = np.array([0.3, -0.5, 1.0])
    luz /= np.linalg.norm(luz)
    allv = []
    for c, m in solid_por_color.items():
        if m.is_empty():
            continue
        mesh = m.to_mesh()
        v = np.asarray(mesh.vert_properties)[:, :3]
        t = np.asarray(mesh.tri_verts)
        tri = v[t]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
        sh = 0.45 + 0.55 * np.clip(n @ luz, 0, 1)
        base = np.array(matplotlib.colors.to_rgb(F.RGB[c]))
        cols = np.clip(base[None, :] * sh[:, None], 0, 1)
        pc = Poly3DCollection(tri, facecolors=cols, edgecolors="none")
        ax.add_collection3d(pc)
        allv.append(v)
    v = np.vstack(allv)
    mn, mx = v.min(0), v.max(0)
    c = (mn + mx) / 2
    r = (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(ruta, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- export
def malla(m):
    mesh = m.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts)


def stl(m, ruta):
    import trimesh
    v, t = malla(m)
    trimesh.Trimesh(v, t, process=False).export(ruta)


def tres_mf(solid_por_color, ruta, nombre="Fenix"):
    """3MF con estructura de Bambu Studio: un objeto con una parte por color y su filamento asignado."""
    partes = [(c, m) for c, m in solid_por_color.items() if not m.is_empty()]
    # centrar en la cama (A1: 256x256)
    allv = np.vstack([malla(m)[0] for _, m in partes])
    mn, mx = allv.min(0), allv.max(0)
    off = np.array([-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]])

    obj_xml = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
               'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
               'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">',
               ' <metadata name="BambuStudio:3mfVersion">1</metadata>', ' <resources>']
    comps = []
    for i, (c, m) in enumerate(partes, start=1):
        v, t = malla(m)
        v = v + off
        obj_xml.append(f'  <object id="{i}" p:UUID="{uuid.uuid4()}" type="model"><mesh><vertices>')
        obj_xml += [f'<vertex x="{a:.4f}" y="{b:.4f}" z="{z:.4f}"/>' for a, b, z in v]
        obj_xml.append('</vertices><triangles>')
        obj_xml += [f'<triangle v1="{a}" v2="{b}" v3="{d}"/>' for a, b, d in t]
        obj_xml.append('</triangles></mesh></object>')
        comps.append((i, c))
    obj_xml += [' </resources>', ' <build/>', '</model>']

    oid = len(partes) + 1
    main = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">',
            ' <metadata name="Application">BambuStudio-02.00.00.00</metadata>',
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
            f' <metadata name="Title">{nombre}</metadata>',
            ' <resources>',
            f'  <object id="{oid}" p:UUID="{uuid.uuid4()}" type="model"><components>']
    for i, c in comps:
        main.append(f'   <component p:path="/3D/Objects/object_1.model" objectid="{i}" '
                    f'p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
    main += ['  </components></object>', ' </resources>',
             f' <build p:UUID="{uuid.uuid4()}"><item objectid="{oid}" p:UUID="{uuid.uuid4()}" '
             'transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/></build>', '</model>']

    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>', f'  <object id="{oid}">',
           f'    <metadata key="name" value="{nombre}"/>', '    <metadata key="extruder" value="1"/>']
    for i, c in comps:
        cfg += [f'    <part id="{i}" subtype="normal_part">',
                f'      <metadata key="name" value="{c}"/>',
                '      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>',
                f'      <metadata key="extruder" value="{F.EXTRUSOR[c]}"/>', '    </part>']
    cfg += ['  </object>', '</config>']

    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    mrels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
             '</Relationships>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(main))
        z.writestr("3D/_rels/3dmodel.model.rels", mrels)
        z.writestr("3D/Objects/object_1.model", "\n".join(obj_xml))
        z.writestr("Metadata/model_settings.config", "\n".join(cfg))


# ---------------------------------------------------------------- comprobaciones
def comprobar(piezas, juntas):
    """Mide holguras reales entre piezas, retención de cada bisagra y giro libre."""
    print("\n== Comprobaciones ==")
    sol = {}
    for p in piezas:
        partes = []
        huella = unary_union(p.huella_extra) if p.huella_extra else Polygon()
        for color, g, h in p.regiones():
            g = F.limpia(g.difference(huella))
            if not g.is_empty:
                partes.append(F.extruir(g, h))
        partes += p.pin3d
        sol[p.nombre] = mf.Manifold.batch_boolean(partes, mf.OpType.Add)
        nc = len(sol[p.nombre].decompose())
        print(f"  {p.nombre:10s} componentes sólidos: {nc} {'OK' if nc == 1 else '¡¡SUELTO!!'}")
    ok = True
    nombres = [p.nombre for p in piezas]
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            a, b = sol[nombres[i]], sol[nombres[j]]
            gap = a.min_gap(b, 2.0)
            if gap < 2.0:
                flag = "OK" if gap >= 0.3 else "¡¡POCA!!"
                ok &= gap >= 0.3
                print(f"  holgura {nombres[i]:9s} - {nombres[j]:9s}: {gap:.2f} mm {flag}")
    return sol, ok


def prueba_giro(sol, pares):
    """Gira B respecto a A alrededor del pivote y mide hasta dónde gira libre."""
    print("\n== Rango de giro libre (sin choque) ==")
    for a, b, c in pares:
        A, B = sol[a], sol[b]
        res = []
        for signo in (1, -1):
            lim = 0
            for ang in np.arange(1, 40, 1):
                Bg = B.translate((-c[0], -c[1], 0)).rotate((0, 0, signo * ang)).translate((c[0], c[1], 0))
                if (A ^ Bg).volume() > 0.05:
                    break
                lim = ang
            res.append(lim)
        print(f"  {b:10s} sobre {a:9s}: +{res[0]}° / -{res[1]}°")


def prueba_retencion(sol, pares):
    """Desplaza B en varias direcciones: la bisagra debe bloquear (choque) antes de 1 mm."""
    print("\n== Retención de bisagras (desplazamiento hasta choque) ==")
    for a, b, c in pares:
        A, B = sol[a], sol[b]
        peor = 0
        for ang in range(0, 360, 30):
            d = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0])
            mov = None
            for s in np.arange(0.1, 3.0, 0.1):
                if (A ^ B.translate(tuple(d * s))).volume() > 0.02:
                    mov = s
                    break
            peor = max(peor, mov if mov is not None else 99)
        for dz in (1, -1):
            mov = None
            for s in np.arange(0.1, 3.0, 0.1):
                if (A ^ B.translate((0, 0, dz * s))).volume() > 0.02:
                    mov = s
                    break
            peor = max(peor, mov if mov is not None else 99)
        print(f"  {b:10s} en {a:9s}: juego máx {peor:.1f} mm {'OK' if peor < 1.5 else '¡¡SE SALE!!'}")


def main(args):
    os.makedirs(OUT, exist_ok=True)
    piezas, juntas = F.diseno()
    vista_plana(piezas, os.path.join(OUT, "vista_plana.png"), juntas, "Fénix flexi - vista superior (mm)")
    if "--rapido" in args:
        return
    sol, ok = comprobar(piezas, juntas)
    pares = [("cuerpo", "cola", juntas[0]["centro"])]
    for k, s in enumerate("DI"):
        pares.append(("cuerpo", f"brazo_{s}", juntas[1 + 2 * k]["centro"]))
        pares.append((f"brazo_{s}", f"ala_{s}", juntas[2 + 2 * k]["centro"]))
    prueba_giro(sol, pares)
    prueba_retencion(sol, pares)

    for eco in (False, True):
        tag = "economico" if eco else "completo"
        spc = F.solidos(piezas, eco=eco)
        d = os.path.join(OUT, f"stl_{tag}")
        os.makedirs(d, exist_ok=True)
        for c, m in spc.items():
            if not m.is_empty():
                stl(m, os.path.join(d, f"fenix_{F.EXTRUSOR[c]}_{c}.stl"))
        tres_mf(spc, os.path.join(OUT, f"fenix_{tag}_A1.3mf"), f"Fenix flexi ({tag})")
        if not eco:
            todo = mf.Manifold.batch_boolean(list(spc.values()), mf.OpType.Add)
            v, _ = malla(todo)
            mn, mx = v.min(0), v.max(0)
            print(f"\nTamaño total: {mx[0]-mn[0]:.1f} x {mx[1]-mn[1]:.1f} x {mx[2]-mn[2]:.1f} mm")
            dens = 1.24e-3  # g/mm3 PLA
            for c, m in spc.items():
                print(f"  {c:9s} volumen {m.volume():7.0f} mm3  ~{m.volume()*dens:.1f} g (100% relleno)")
    print("\nArchivos en", OUT)
