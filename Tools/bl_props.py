"""Kapadokya mimarisi ve kulturel unsurlar: Blender'da parametrik uretim.

Her varlik RawAssets/kmsh/<Ad>.kmsh olur. Materyal slotlari ue_import_assets.py ile eslenir:
  Stone, StoneWall, Plaster, Roof, Wood, Tuff, Color(A/B/C...), Glass, Metal
UV0 metre cinsindendir (materyaller Tile ile olcekler). Koseler Vertex Color tasir.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

import bl_common as C

SLOTS_ARCH = {"Stone": 0, "StoneWall": 1, "Plaster": 2, "Roof": 3, "Wood": 4, "Dark": 5, "Metal": 6, "Glass": 7, "ColorA": 8, "ColorB": 9, "ColorC": 10}


def mats():
    return {k: C.mat(k) for k in SLOTS_ARCH}


def world_uv(obj, tint=None, jitter=0.0):
    """Kutu yansitmali metre-UV ve istege bagli koyu kose rengi."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UV")
    uv = me.uv_layers.active
    mw = obj.matrix_world
    nm = mw.to_3x3()
    for poly in me.polygons:
        n = (nm @ poly.normal)
        a = abs(n.x), abs(n.y), abs(n.z)
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if a[2] >= a[0] and a[2] >= a[1]:
                uv.uv[li].vector = (co.x, 1 - co.y)
            elif a[0] >= a[1]:
                uv.uv[li].vector = (co.y, 1 - co.z)
            else:
                uv.uv[li].vector = (co.x, 1 - co.z)
    return obj


def parts_bake(parts):
    for p in parts:
        bpy.context.view_layer.update()
        world_uv(p)


def bevel(obj, amount=0.02, seg=2):
    m = obj.modifiers.new("b", "BEVEL")
    m.width = amount
    m.segments = seg
    m.limit_method = "ANGLE"
    return obj


def weight_ao(obj, strength=0.45):
    """Yukseklige gore koselere taban kirlenmesi yazar (vertex color)."""
    me = obj.data
    if "Col" not in me.color_attributes:
        me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    col = me.color_attributes["Col"]
    mw = obj.matrix_world
    for i, lp in enumerate(me.loops):
        co = mw @ me.vertices[lp.vertex_index].co
        grime = max(0.0, 1.0 - co.z / 2.2) * strength
        n = noise.noise(co * 0.8) * 0.12
        v = max(0.25, 1.0 - grime + n)
        col.data[i].color = (v, v * 0.98, v * 0.94, 1)
    return obj


# ------------------------------------------------------------- Peribacasi
def displaced_lathe(name, profile, material, seed, seg=96, rings=None, disp=0.18, strata=0.12, sharp=0.0):
    """Dikey profil: (yukseklik, yaricap). Gurultuyle yerinden oynatir; strata yatay katman verir."""
    rings = rings or len(profile) * 8
    zs = np.array([p[0] for p in profile], float)
    rs = np.array([p[1] for p in profile], float)
    verts, faces = [], []
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for j in range(rings):
        u = j / (rings - 1)
        z = zs[0] + (zs[-1] - zs[0]) * u
        r = np.interp(z, zs, rs)
        layer = noise.noise(Vector((0, 0, z * 0.9)) + off) * strata
        for i in range(seg):
            a = 2 * math.pi * i / seg
            d = Vector((math.cos(a), math.sin(a), 0))
            p = d * r
            q = Vector((p.x, p.y, z)) * 0.55 + off
            n1 = noise.fractal(q, 1.0, 2.0, 5) * disp * (0.7 + r * 0.25)
            n2 = noise.noise(Vector((p.x * 3, p.y * 3, z * 8)) + off) * 0.03
            rr = max(0.03, r * (1 + n1) + layer * (0.6 + r * 0.15) + n2)
            verts.append((d.x * rr, d.y * rr, z + noise.noise(q * 2) * 0.06))
    for j in range(rings - 1):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            c = (j + 1) * seg + (i + 1) % seg
            dd = (j + 1) * seg + i
            faces.append((a, b, c, dd))
    faces.append(tuple(range(seg))[::-1])
    faces.append(tuple((rings - 1) * seg + i for i in range(seg)))
    o = C.from_pydata(name, verts, faces, material)
    return o


def fairy_chimney(idx, seed, H, base_r, cap_r, cap_h):
    """Uclu yapi: genis tuf etek, ince govde, koyu bazalt sapka."""
    m = mats()
    random.seed(seed)
    neck = H * random.uniform(0.70, 0.78)
    prof = [(-1.5, base_r * 1.2), (0.0, base_r), (H * 0.2, base_r * 0.8), (H * 0.42, base_r * 0.6), (neck * 0.82, base_r * 0.4), (neck, base_r * 0.3)]
    shaft = displaced_lathe("shaft", prof, m["Plaster"], seed, seg=110, rings=90, disp=0.14)
    capp = [(neck - 0.3, base_r * 0.20), (neck, cap_r * 0.72), (neck + cap_h * 0.25, cap_r), (neck + cap_h * 0.7, cap_r * 0.72), (neck + cap_h, cap_r * 0.08)]
    hat = displaced_lathe("hat", capp, m["Dark"], seed + 3, seg=72, rings=36, disp=0.20, strata=0.05)
    world_uv(shaft)
    world_uv(hat)
    return [shaft, hat]


# ------------------------------------------------------------- Mimari yardimcilari
def wall_box(name, center, size, material):
    o = C.box(name, center, size, material)
    bpy.context.view_layer.update()
    # Kutuyu uygulanmis donusume cek
    me = o.data
    me.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    world_uv(o)
    return o


def window(x, y, z, w, h, axis, depth=0.12, arch=False):
    """axis: 'x' yuzeyi X'te ilerler (normali Y). Pencere pervazi + koyu cam + kafes."""
    m = mats()
    out = []
    if axis == "x":
        frame_size = (w + 0.16, 0.08, h + 0.16)
        glass_size = (w, 0.11, h)
    else:
        frame_size = (0.08, w + 0.16, h + 0.16)
        glass_size = (0.11, w, h)
    out.append(wall_box("wf", (x, y, z), frame_size, m["Stone"]))
    out.append(wall_box("wg", (x, y, z), glass_size, m["Glass"]))
    # Kafes cubuklari
    bars = 3
    for i in range(1, bars):
        u = -w / 2 + w * i / bars
        if axis == "x":
            out.append(wall_box("wb", (x + u, y, z), (0.03, 0.14, h), m["Wood"]))
        else:
            out.append(wall_box("wb", (x, y + u, z), (0.14, 0.03, h), m["Wood"]))
    return out


def hip_roof(cx, cy, z, lx, ly, h, overhang=0.35):
    """Kiremit catisi: dort yani egimli, altinda sacak."""
    m = mats()
    x0, x1 = cx - lx / 2 - overhang, cx + lx / 2 + overhang
    y0, y1 = cy - ly / 2 - overhang, cy + ly / 2 + overhang
    rx = max(lx, ly) * 0.25 if lx >= ly else 0.0
    ry = max(lx, ly) * 0.25 if ly > lx else 0.0
    v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z),
         (cx - (lx / 2 - min(lx, ly) / 2), cy - (ly / 2 - min(lx, ly) / 2), z + h),
         (cx + (lx / 2 - min(lx, ly) / 2), cy + (ly / 2 - min(lx, ly) / 2), z + h)]
    if lx >= ly:
        f = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)]
    else:
        f = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5)]
    if lx >= ly:
        v[4] = (cx - (lx - ly) / 2, cy, z + h)
        v[5] = (cx + (lx - ly) / 2, cy, z + h)
    else:
        v[4] = (cx, cy - (ly - lx) / 2, z + h)
        v[5] = (cx, cy + (ly - lx) / 2, z + h)
    r = C.from_pydata("roof", v, f, m["Roof"], smooth=False)
    # Egime paralel UV
    me = r.data
    me.uv_layers.new(name="UV")
    uv = me.uv_layers.active
    for poly in me.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            along = co.x if abs(n.y) > abs(n.x) else co.y
            run = (co.y if abs(n.y) > abs(n.x) else co.x) / max(0.4, abs(n.z))
            uv.uv[li].vector = (along, run)
    eave = wall_box("eave", (cx, cy, z - 0.07), (lx + overhang * 2 + 0.06, ly + overhang * 2 + 0.06, 0.14), m["Wood"])
    return [r, eave]


def konak(idx, seed, floors=2, lx=9.0, ly=7.0):
    """Taş zemin + cikmali ahsap/sivali ust kat + kiremit. Giris yuzu -Y (yola bakar)."""
    m = mats()
    rnd = random.Random(seed)
    parts = []
    z = 0.0
    fh0 = rnd.uniform(3.0, 3.4)
    parts.append(wall_box("base", (0, 0, fh0 / 2 - 0.3), (lx, ly, fh0 + 0.6), m["StoneWall"]))
    parts.append(wall_box("plinth", (0, 0, 0.15), (lx + 0.12, ly + 0.12, 0.5), m["Stone"]))
    z = fh0
    # Kapi + kemer
    parts.append(wall_box("door", (rnd.uniform(-1.5, 1.5), -ly / 2 - 0.02, 1.15), (1.15, 0.1, 2.3), m["Wood"]))
    parts.append(wall_box("doorarch", (parts[-1].data.vertices[0].co.x + 0.57, -ly / 2 - 0.02, 2.42), (1.4, 0.14, 0.28), m["Stone"]))
    for sx in (-lx * 0.34, lx * 0.34):
        parts += window(sx, -ly / 2 - 0.04, 1.75, 0.7, 1.15, "x")
    for sy in (-ly * 0.25, ly * 0.25):
        parts += window(-lx / 2 - 0.04, sy, 1.75, 0.7, 1.15, "y")
        parts += window(lx / 2 + 0.04, sy, 1.75, 0.7, 1.15, "y")
    # Ust kat: cikma
    for f in range(floors - 1):
        jut = 0.55 if f == 0 else 0.15
        fh = rnd.uniform(2.75, 3.0)
        ulx, uly = lx + jut * 2, ly + jut * 2
        parts.append(wall_box("upper", (0, 0, z + fh / 2), (ulx, uly, fh), m["Plaster"]))
        # Ahsap hatil ve dikmeler
        for hz in (z + 0.06, z + fh - 0.06):
            parts.append(wall_box("hatil", (0, 0, hz), (ulx + 0.08, uly + 0.08, 0.12), m["Wood"]))
        for k in range(7):
            u = -ulx / 2 + ulx * k / 6
            parts.append(wall_box("dikme", (u, -uly / 2 - 0.03, z + fh / 2), (0.1, 0.07, fh), m["Wood"]))
        if f == 0:
            for k in range(6):
                u = -ulx / 2 + ulx * (k + 0.5) / 6
                brace = C.box("brace", (u, -ly / 2 - jut / 2, z - 0.28), (0.1, jut + 0.1, 0.1), m["Wood"], rot=(math.radians(38), 0, 0))
                parts.append(brace)
        n = 4
        for k in range(n):
            u = -ulx / 2 + ulx * (k + 0.5) / n
            parts += window(u, -uly / 2 - 0.05, z + fh * 0.53, 0.72, 1.4, "x")
        for k in range(3):
            u = -uly / 2 + uly * (k + 0.5) / 3
            parts += window(ulx / 2 + 0.05, u, z + fh * 0.53, 0.72, 1.4, "y")
            parts += window(-ulx / 2 - 0.05, u, z + fh * 0.53, 0.72, 1.4, "y")
        z += fh
    parts += hip_roof(0, 0, z, ulx, uly, rnd.uniform(1.8, 2.3), 0.45)
    # Baca
    parts.append(wall_box("chimney", (lx * 0.3, ly * 0.15, z + 2.1), (0.6, 0.6, 2.2), m["StoneWall"]))
    parts.append(wall_box("chimcap", (lx * 0.3, ly * 0.15, z + 3.25), (0.8, 0.8, 0.1), m["Stone"]))
    return parts


def magara_ev(seed):
    """Kayaya oyulmus tuf ev: kaba kutle, kemerli kapi ve pencereler."""
    m = mats()
    rnd = random.Random(seed)
    H = rnd.uniform(9, 14)
    prof = [(-1, 8.5), (0, 8.0), (H * 0.4, 7.0), (H * 0.8, 5.2), (H, 2.2), (H + 1.2, 0.3)]
    rock = displaced_lathe("rock", prof, m["Plaster"], seed, seg=120, rings=70, disp=0.12)
    world_uv(rock)
    parts = [rock]
    for k in range(rnd.randint(5, 8)):
        ang = -math.pi / 2 + rnd.uniform(-1.0, 1.0)
        z = rnd.uniform(1.0, H * 0.72)
        r = np.interp(z, [p[0] for p in prof], [p[1] for p in prof]) * 0.98
        x, y = math.cos(ang) * r, math.sin(ang) * r
        s = rnd.uniform(0.7, 1.05)
        w = C.box("hole", (x, y, z), (s, 0.6, s * 1.4), m["Dark"], rot=(0, 0, ang + math.pi / 2))
        parts.append(w)
        w2 = C.box("sill", (x * 1.01, y * 1.01, z - s * 0.74), (s * 1.2, 0.5, 0.12), m["Stone"], rot=(0, 0, ang + math.pi / 2))
        parts.append(w2)
    for p in parts[1:]:
        world_uv(p)
    return parts


def cami():
    """Tek kubbeli klasik Osmanli camisi + sadirvan + tek serefeli minare. Giris -Y."""
    m = mats()
    parts = []
    W, D, H = 14.0, 14.0, 9.0
    parts.append(wall_box("harim", (0, 0, H / 2), (W, D, H), m["Stone"]))
    # Kose payandalari
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(wall_box("buttress", (sx * W * 0.5, sy * D * 0.5, H * 0.55), (1.0, 1.0, H * 1.1), m["Stone"]))
    # Pencereler iki sira, sivri kemer etkisi
    for row, z, h in ((0, 2.7, 1.9), (1, 6.3, 1.5)):
        for k in range(4):
            u = -W / 2 + W * (k + 0.5) / 4
            parts += window(u, -D / 2 - 0.05, z, 1.0, h, "x")
            parts += window(u, D / 2 + 0.05, z, 1.0, h, "x")
            parts += window(-W / 2 - 0.05, u, z, 1.0, h, "y")
            parts += window(W / 2 + 0.05, u, z, 1.0, h, "y")
    # Kubbe kasnagi
    drum = C.lathe("drum", [(5.8, 0), (5.8, 1.3), (5.95, 1.35)], m["Stone"], axis_center=(0, 0, 0), segments=64)
    drum.rotation_euler = (math.radians(90), 0, 0)
    drum.location = (0, 0, H)
    parts.append(drum)
    # Kurşun kubbe
    prof = []
    Rd = 5.9
    for i in range(24):
        t = i / 23 * math.pi / 2
        prof.append((Rd * math.cos(t), Rd * math.sin(t) * 0.95))
    dome = C.lathe("dome", prof + [(0.02, Rd * 0.96)], m["Metal"], segments=72)
    dome.rotation_euler = (math.radians(90), 0, 0)
    dome.location = (0, 0, H + 1.35)
    parts.append(dome)
    # Alem
    for dz, r, h in ((0.0, 0.12, 0.6), (0.65, 0.22, 0.28), (1.0, 0.13, 0.22), (1.25, 0.05, 0.6)):
        parts.append(C.cylinder("alem", (0, 0, H + 1.35 + Rd * 0.94 + dz), (0, 0, H + 1.35 + Rd * 0.94 + dz + h), r, m["ColorC"], 14))
    # Son cemaat revagi: kemerli sutunlar
    pz = D / 2 + 3.2
    parts.append(wall_box("porch_roof", (0, -pz, 5.4), (W + 1.2, 6.2, 0.45), m["Stone"]))
    parts.append(wall_box("porch_lead", (0, -pz, 5.72), (W + 1.5, 6.5, 0.2), m["Metal"]))
    for k in range(6):
        u = -W / 2 + W * k / 5
        parts.append(C.cylinder("col", (u, -pz - 2.8, 0), (u, -pz - 2.8, 4.6), 0.28, m["Stone"], 20))
        parts.append(wall_box("capital", (u, -pz - 2.8, 4.75), (0.72, 0.72, 0.3), m["Stone"]))
    parts.append(wall_box("lintel", (0, -pz - 2.8, 5.0), (W + 0.6, 0.5, 0.5), m["Stone"]))
    # Tac kapi: mukarnas etkisi veren kademeli nis
    for lvl in range(6):
        wid = 3.0 - lvl * 0.34
        parts.append(wall_box("tac", (0, -D / 2 - 0.12 - (5 - lvl) * 0.02, 3.2 + lvl * 0.42), (wid, 0.24, 0.4), m["Stone"]))
    parts.append(wall_box("door", (0, -D / 2 - 0.08, 1.4), (1.6, 0.1, 2.8), m["Wood"]))
    # Minare (govdeden ayri, kosede)
    mx, my = W / 2 + 2.4, -D / 2 + 0.8
    parts.append(wall_box("min_base", (mx, my, 3.5), (3.0, 3.0, 7.0), m["Stone"]))
    parts.append(C.cylinder("min_trans", (mx, my, 7.0), (mx, my, 8.2), 1.52, m["Stone"], 16, 1.18))
    # Kaval govde: oniki kenarli
    parts.append(C.cylinder("min_shaft", (mx, my, 8.2), (mx, my, 26.0), 1.15, m["Stone"], 16, 0.98))
    # Serefe
    parts.append(C.cylinder("seref_under", (mx, my, 25.0), (mx, my, 26.4), 1.0, m["Stone"], 16, 1.55))
    parts.append(C.cylinder("seref_floor", (mx, my, 26.4), (mx, my, 26.65), 1.65, m["Stone"], 24))
    for k in range(18):
        a = 2 * math.pi * k / 18
        parts.append(C.cylinder("rail", (mx + math.cos(a) * 1.55, my + math.sin(a) * 1.55, 26.65), (mx + math.cos(a) * 1.55, my + math.sin(a) * 1.55, 27.65), 0.045, m["Stone"], 6))
    parts.append(C.cylinder("rail_top", (mx, my, 27.65), (mx, my, 27.75), 1.62, m["Stone"], 24))
    parts.append(C.cylinder("min_top", (mx, my, 26.65), (mx, my, 31.0), 0.88, m["Stone"], 16))
    parts.append(C.cylinder("min_cone", (mx, my, 31.0), (mx, my, 36.0), 0.95, m["Metal"], 16, 0.02))
    parts.append(C.cylinder("min_alem", (mx, my, 35.8), (mx, my, 37.0), 0.05, m["ColorC"], 8))
    for p in parts:
        if p.data.uv_layers:
            continue
        bpy.context.view_layer.update()
        world_uv(p)
    return parts


def kervansaray():
    """Selcuklu tac kapili kervansaray cephesi; ic avlu duvarlari ve kuleler. Cephe -Y."""
    m = mats()
    parts = []
    W, D, H = 46.0, 34.0, 8.5
    parts.append(wall_box("front_l", (-W * 0.31, -D / 2, H / 2), (W * 0.38, 2, H), m["Stone"]))
    parts.append(wall_box("front_r", (W * 0.31, -D / 2, H / 2), (W * 0.38, 2, H), m["Stone"]))
    parts.append(wall_box("back", (0, D / 2, H / 2), (W, 2, H), m["Stone"]))
    parts.append(wall_box("side_l", (-W / 2, 0, H / 2), (2, D, H), m["Stone"]))
    parts.append(wall_box("side_r", (W / 2, 0, H / 2), (2, D, H), m["Stone"]))
    # Kule payandalari: cokgen
    for k in range(5):
        u = -W / 2 + W * k / 4
        for yy in (-D / 2, D / 2):
            parts.append(C.cylinder("tower", (u, yy, 0), (u, yy, H + 0.7), 2.1, m["Stone"], 8, 1.85))
    for yy in (-D / 6, D / 6):
        for xx in (-W / 2, W / 2):
            parts.append(C.cylinder("tower", (xx, yy, 0), (xx, yy, H + 0.7), 1.9, m["Stone"], 8, 1.7))
    # Tac kapi: yukselen mukarnas ni
    gx, gy = 0, -D / 2
    GW = 9.0
    GH = 14.0
    parts.append(wall_box("gate_mass_l", (-GW * 0.4, gy - 0.5, GH / 2), (GW * 0.26, 3.0, GH), m["Stone"]))
    parts.append(wall_box("gate_mass_r", (GW * 0.4, gy - 0.5, GH / 2), (GW * 0.26, 3.0, GH), m["Stone"]))
    parts.append(wall_box("gate_top", (0, gy - 0.5, GH - 1.0), (GW, 3.0, 2.0), m["Stone"]))
    # Sivri kemer kemerleri: katmanli
    for ring in range(6):
        rr = 2.9 - ring * 0.32
        depth = gy - 0.8 + ring * 0.42
        pts = []
        for i in range(20):
            t = i / 19
            a = math.pi * (1 - t)
            # Iki merkezli sivri kemer
            sign = -1 if a > math.pi / 2 else 1
            cx = sign * rr * -0.26
            xx = cx + rr * 1.26 * math.cos(a)
            zz = 6.6 + rr * 1.26 * math.sin(a) * 0.96
            pts.append((xx, depth, zz))
        for i in range(len(pts) - 1):
            parts.append(C.cylinder("arch", pts[i], pts[i + 1], 0.2, m["StoneWall" if ring % 2 else "Stone"], 8))
        for sx in (-1, 1):
            parts.append(C.cylinder("jamb", (sx * rr, depth, 0), (sx * rr, depth, 6.7), 0.2, m["Stone"], 12))
    # Mukarnas kademeleri (geometrik nisler)
    for lvl in range(7):
        n = 11 - lvl
        for k in range(n):
            u = (k - (n - 1) / 2) * (6.0 / 11)
            parts.append(wall_box("muq", (u, gy + 1.15, 6.9 + lvl * 0.62), (0.46, 0.44 + lvl * 0.05, 0.56), m["Stone"]))
    # Yuzeydeki geometrik kusak (Selcuklu yildizi yerine sade zigzag)
    for z in (1.5, 3.4, 5.4):
        parts.append(wall_box("bant", (0, gy - 2.05, z), (GW + 0.2, 0.14, 0.16), m["StoneWall"]))
    parts.append(wall_box("door_l", (-2.2, gy + 0.8, 1.9), (0.1, 1.2, 3.8), m["Wood"]))
    parts.append(wall_box("door_r", (2.2, gy + 0.8, 1.9), (0.1, 1.2, 3.8), m["Wood"]))
    return parts


def kopru():
    """Tas kemerli Osmanli koprusu: uc kemer. Uzunluk X ekseninde 70 m (yol uzerinden gecer).

    Merkez kemer, yol kotunun altinda. Ust yuzey yol seridi ile kapanir.
    """
    m = mats()
    parts = []
    Ln, Wd = 70.0, 8.6
    bottom = -8.0
    # Ana kitle: kemer aciklikli yan duvarlar
    for side in (-1, 1):
        y = side * (Wd / 2 - 0.35)
        verts, faces = [], []
        xs = np.linspace(-Ln / 2, Ln / 2, 180)
        arches = [(-20.0, 9.0), (0.0, 12.0), (20.0, 9.0)]
        tops, bots = [], []
        for x in xs:
            z_arch = bottom
            for cx, r in arches:
                if abs(x - cx) < r:
                    # Hafif sivri kemer
                    z_arch = max(z_arch, bottom + 0.8 * r * math.sqrt(max(0, 1 - ((x - cx) / r) ** 2)) * 1.05)
            tops.append(0.4 + 0.5 * (1 - (x / (Ln / 2)) ** 2) * 0)
            bots.append(z_arch)
        n = len(xs)
        for i in range(n):
            verts.append((xs[i], y, bots[i]))
            verts.append((xs[i], y, tops[i]))
        for i in range(n - 1):
            a, b, c, d = 2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1
            faces.append((a, b, c, d) if side < 0 else (d, c, b, a))
        o = C.from_pydata("spandrel", verts, faces, m["StoneWall"], smooth=False)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        ret = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        moved = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, -side * 0.7, 0), verts=moved)
        bm.to_mesh(o.data)
        bm.free()
        world_uv(o)
        parts.append(o)
        # Korkuluk: alcak tas parapet
        parts.append(wall_box("parapet", (0, side * (Wd / 2 - 0.25), 0.8), (Ln + 2, 0.5, 1.0), m["Stone"]))
        parts.append(wall_box("rail_cap", (0, side * (Wd / 2 - 0.25), 1.34), (Ln + 2, 0.66, 0.1), m["Stone"]))
    # Kemer alti tonoz: yatay plakalar
    for cx, r in ((-20.0, 9.0), (0.0, 12.0), (20.0, 9.0)):
        N = 28
        for i in range(N):
            t0 = -1 + 2 * i / N
            t1 = -1 + 2 * (i + 1) / N
            z0 = bottom + 0.8 * r * math.sqrt(max(0, 1 - t0 ** 2)) * 1.05
            z1 = bottom + 0.8 * r * math.sqrt(max(0, 1 - t1 ** 2)) * 1.05
            mx, mz = cx + r * (t0 + t1) / 2, (z0 + z1) / 2
            sl = math.hypot(r * (t1 - t0), z1 - z0)
            ang = math.atan2(z1 - z0, r * (t1 - t0))
            parts.append(C.box("vault", (mx, 0, mz), (sl + 0.05, Wd, 0.5), m["Stone"], rot=(0, -ang, 0)))
    # Ayaklar
    for cx in (-10.0, 10.0):
        parts.append(wall_box("pier", (cx, 0, bottom - 1.0), (6.5, Wd + 0.6, 3.0), m["StoneWall"]))
    # Sivri su kirici
    for cx in (-10.0, 10.0):
        for side in (-1, 1):
            parts.append(C.cylinder("cutwater", (cx, side * (Wd / 2 + 0.3), bottom - 2), (cx, side * (Wd / 2 + 0.3), bottom + 2.2), 2.6, m["Stone"], 4, 0.5))
    for p in parts:
        if not p.data.uv_layers:
            bpy.context.view_layer.update()
            world_uv(p)
    return parts


def cesme():
    """Osmanli sebili/cesmesi: taş ayna, kemer, oluk, yalak, sacak."""
    m = mats()
    parts = [wall_box("mirror", (0, 0, 1.55), (2.3, 0.4, 3.1), m["Stone"]), wall_box("eave", (0, -0.1, 3.2), (3.0, 0.8, 0.14), m["Stone"])]
    parts.append(wall_box("niche", (0, -0.22, 1.55), (1.4, 0.08, 2.0), m["StoneWall"]))
    parts.append(wall_box("trough", (0, -0.6, 0.35), (2.0, 0.65, 0.7), m["Stone"]))
    parts.append(wall_box("water", (0, -0.6, 0.65), (1.8, 0.48, 0.05), m["Glass"]))
    parts.append(C.cylinder("spout", (0, -0.22, 1.1), (0, -0.56, 1.03), 0.035, m["ColorC"], 10))
    for sx in (-1, 1):
        parts.append(wall_box("col", (sx * 0.95, -0.25, 1.5), (0.16, 0.14, 2.8), m["Stone"]))
    for p in parts:
        if not p.data.uv_layers:
            bpy.context.view_layer.update()
            world_uv(p)
    return parts


def tente_stall(idx, seed):
    """Carsi tezgahi: ahsap dikme, kilim desenli tente ve urun kasalari. On yuz -Y."""
    m = mats()
    rnd = random.Random(seed)
    parts = []
    w, d = 4.2, 2.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.cylinder("post", (sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, 2.6 if sy > 0 else 2.2), 0.05, m["Wood"], 8))
    # Tente: koseye gore vertex-renkli kilim
    res = 42
    verts, faces = [], []
    for j in range(res + 1):
        for i in range(res + 1):
            u, v = i / res, j / res
            x, y = (u - 0.5) * (w + 0.55), (v - 0.5) * (d + 0.5)
            z = 2.2 + v * 0.5 - 0.06 * math.sin(u * math.pi) * (1 - v)
            verts.append((x, y, z))
    for j in range(res):
        for i in range(res):
            a = j * (res + 1) + i
            faces.append((a, a + 1, a + res + 2, a + res + 1))
    t = C.from_pydata("tente", verts, faces, m["ColorA"])
    t.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    col = t.data.color_attributes["Col"]
    palette = [(0.55, 0.05, 0.05), (0.85, 0.72, 0.5), (0.07, 0.12, 0.33), (0.75, 0.35, 0.05), (0.12, 0.30, 0.24)]
    A, B, C2 = rnd.sample(palette, 3)
    for j in range(res + 1):
        for i in range(res + 1):
            u, v = i / res, j / res
            # Kilim gobegi: elibelinde turu baklava motifi
            cu, cv = abs(u - 0.5) * 2, abs(v - 0.5) * 2
            border = cu > 0.86 or cv > 0.82
            k = ((u * 6) % 1 - 0.5, (v * 4) % 1 - 0.5)
            diamond = abs(k[0]) + abs(k[1])
            c = C2 if border else (B if diamond < 0.28 else A)
            if not border and 0.28 < diamond < 0.36:
                c = (0.92, 0.88, 0.72)
            col.data[j * (res + 1) + i].color = (*c, 1)
    world_uv(t)
    parts.append(t)
    # Tezgah
    parts.append(wall_box("table", (0, -0.2, 0.85), (w - 0.25, 1.1, 0.08), m["Wood"]))
    parts.append(wall_box("table_front", (0, -0.75, 0.42), (w - 0.25, 0.04, 0.82), m["Wood"]))
    # Urun: renkli kasalar (kayisi, nar, baharat)
    fruits = [(0.85, 0.42, 0.05), (0.62, 0.05, 0.06), (0.75, 0.55, 0.08), (0.08, 0.28, 0.12)]
    for k in range(5):
        u = -w * 0.38 + w * 0.19 * k
        fc = fruits[rnd.randrange(4)]
        crate = wall_box("crate", (u, -0.25, 0.97), (0.72, 0.62, 0.16), m["Wood"])
        parts.append(crate)
        fr = C.box("fruit", (u, -0.25, 1.09), (0.62, 0.52, 0.12), m["ColorB"])
        fr.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
        for dat in fr.data.color_attributes["Col"].data:
            dat.color = (*fc, 1)
        world_uv(fr)
        parts.append(fr)
    return parts


def cay_masa():
    """Cay bahcesi: masa, tabureler, ince belli cay bardagi."""
    m = mats()
    parts = [C.cylinder("top", (0, 0, 0.72), (0, 0, 0.75), 0.42, m["Wood"], 24), C.cylinder("leg", (0, 0, 0), (0, 0, 0.72), 0.04, m["Dark"], 10)]
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        x, y = math.cos(a) * 0.75, math.sin(a) * 0.75
        parts.append(C.cylinder("stool", (x, y, 0.42), (x, y, 0.46), 0.18, m["Wood"], 16))
        parts.append(C.cylinder("stoolleg", (x, y, 0), (x, y, 0.42), 0.025, m["Dark"], 6))
    for k in range(3):
        a = k * 2.1
        x, y = math.cos(a) * 0.22, math.sin(a) * 0.22
        parts.append(C.cylinder("saucer", (x, y, 0.75), (x, y, 0.757), 0.055, m["Metal"], 16))
        parts.append(C.cylinder("tea1", (x, y, 0.757), (x, y, 0.80), 0.022, m["ColorA"], 12, 0.03))
        parts.append(C.cylinder("tea2", (x, y, 0.80), (x, y, 0.855), 0.03, m["ColorA"], 12, 0.024))
    for p in parts:
        if not p.data.uv_layers:
            bpy.context.view_layer.update()
            world_uv(p)
    return parts


def balloon(idx, palette):
    """Kapadokya sicak hava balonu: renkli dilimler ve sepet."""
    m = mats()
    prof = []
    H = 22.0
    for i in range(36):
        t = i / 35
        z = t * H
        r = 9.8 * (math.sin(math.pi * (0.1 + t * 0.88)) ** 0.75) * (0.3 + 0.7 * min(1, t * 2.5))
        if t < 0.08:
            r = max(r, 1.5 + 8 * t)
        prof.append((r, z))
    seg = 96
    verts, faces = [], []
    for s in range(seg):
        a = 2 * math.pi * s / seg
        puff = 1 + 0.03 * abs(math.sin(a * 8))
        for r, z in prof:
            verts.append((r * puff * math.cos(a), r * puff * math.sin(a), z))
    n = len(prof)
    for s in range(seg):
        s2 = (s + 1) % seg
        for j in range(n - 1):
            faces.append((s * n + j, s2 * n + j, s2 * n + j + 1, s * n + j + 1))
    o = C.from_pydata("env", verts, faces, m["ColorA"])
    o.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    col = o.data.color_attributes["Col"]
    for s in range(seg):
        band = (s // 8) % len(palette)
        for j in range(n):
            c = palette[band]
            if 12 <= j <= 15:
                c = palette[(band + 1) % len(palette)]
            if 21 <= j <= 22:
                c = (0.92, 0.88, 0.72)
            col.data[s * n + j].color = (*c, 1)
    world_uv(o)
    parts = [o]
    parts.append(wall_box("basket", (0, 0, -4.2), (1.5, 1.5, 1.1), m["Wood"]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(C.cylinder("rope", (sx * 0.7, sy * 0.7, -3.65), (sx * 1.3, sy * 1.3, 1.0), 0.015, m["Dark"], 5))
    return parts


def bayrak(H=7.0):
    """Direk ve Turk bayragi; UE tarafinda ruzgar WPO'su uygulanir."""
    m = mats()
    pole = C.cylinder("pole", (0, 0, 0), (0, 0, H), 0.045, m["Metal"], 12, 0.03)
    world_uv(pole)
    knob = C.cylinder("knob", (0, 0, H), (0, 0, H + 0.1), 0.06, m["ColorC"], 12, 0.02)
    world_uv(knob)
    w, h = 1.8, 1.2
    res_x, res_y = 72, 48
    verts, faces = [], []
    cx, cy = 0.5 * h, h * 0.5   # Ay merkezi (standart oranlara yakin)
    for j in range(res_y + 1):
        for i in range(res_x + 1):
            u, v = i / res_x, j / res_y
            x, z = u * w, H - 0.08 - v * h
            verts.append((x, 0, z))
    for j in range(res_y):
        for i in range(res_x):
            a = j * (res_x + 1) + i
            faces.append((a, a + res_x + 1, a + res_x + 2, a + 1))
    f = C.from_pydata("flag", verts, faces, m["ColorB"])
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    col = f.data.color_attributes["Col"]
    # Ay yildiz: bayrak kanunu oranlarina yakin
    G = h
    moon_c = (0.5 * G, 0.5 * G)
    moon_r = 0.25 * G
    inner_c = (moon_c[0] + 0.0625 * G, 0.5 * G)
    inner_r = 0.2 * G
    star_c = (moon_c[0] + 0.0625 * G + 0.2 * G + 0.1 * G, 0.5 * G)
    star_r = 0.125 * G
    def in_star(px, py):
        dx, dy = px - star_c[0], py - star_c[1]
        r = math.hypot(dx, dy)
        if r > star_r:
            return False
        ang = (math.atan2(dy, dx) - math.pi / 2) % (2 * math.pi / 5)
        ang = abs(ang - math.pi / 5)
        rr = star_r * 0.38 * math.cos(math.pi / 5) / max(1e-6, math.cos(ang - 0))
        k = math.cos(math.pi * 2 / 5) / math.cos(math.pi / 5)
        # Bes kollu yildiz sinir yaricapi
        boundary = star_r * math.cos(math.pi / 5) / math.cos((math.pi / 5) - ang)
        return r < boundary * 0.62
    white = (0.95, 0.95, 0.95, 1)
    red = (0.70, 0.015, 0.02, 1)
    for j in range(res_y + 1):
        for i in range(res_x + 1):
            u, v = i / res_x, j / res_y
            px = u * w
            py = v * h
            d1 = math.hypot(px - moon_c[0], py - moon_c[1])
            d2 = math.hypot(px - inner_c[0], py - inner_c[1])
            on = (d1 <= moon_r and d2 >= inner_r) or in_star(px, py)
            col.data[j * (res_x + 1) + i].color = white if on else red
    world_uv(f)
    # Rüzgarda kivrim WPO dalgasi icin UV2 yerine u degerini vertex alpha tasiyabiliriz: u = alpha
    for j in range(res_y + 1):
        for i in range(res_x + 1):
            c = list(col.data[j * (res_x + 1) + i].color)
            c[3] = i / res_x
            col.data[j * (res_x + 1) + i].color = c
    return [pole, knob, f]


def flama_ipi():
    """Cadde ustu flama dizisi: 18 m boyunca kirmizi-beyaz ucgenler."""
    m = mats()
    L = 18.0
    verts, faces, cols = [], [], []
    k = 22
    for i in range(k):
        x = (i + 0.5) / k * L - L / 2
        sag = -0.8 * (1 - (2 * (i + 0.5) / k - 1) ** 2)
        a = len(verts)
        verts += [(x - 0.3, 0, sag), (x + 0.3, 0, sag), (x, 0, sag - 0.62)]
        faces.append((a, a + 2, a + 1))
        cols.append((0.72, 0.02, 0.03, 1) if i % 2 == 0 else (0.92, 0.92, 0.9, 1))
    f = C.from_pydata("flama", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(3):
            f.data.color_attributes["Col"].data[i * 3 + t].color = c
    world_uv(f)
    rope = C.tube("rope", [(-L / 2, 0, 0), (0, 0, -0.85), (L / 2, 0, 0)], 0.008, m["Dark"], 6)
    world_uv(rope)
    return [f, rope]


def bariyer():
    """Yaris bariyeri: metal cit ve sponsor panosu (kurmaca kurumlar). Uzunluk 2.5 m."""
    m = mats()
    parts = []
    for z in (0.12, 1.08):
        parts.append(C.cylinder("rail", (-1.25, 0, z), (1.25, 0, z), 0.018, m["Metal"], 8))
    for x in (-1.25, 1.25):
        parts.append(C.cylinder("post", (x, 0, 0), (x, 0, 1.1), 0.02, m["Metal"], 8))
        parts.append(C.cylinder("foot", (x, -0.3, 0.02), (x, 0.3, 0.02), 0.02, m["Metal"], 8))
    b = wall_box("banner", (0, -0.03, 0.62), (2.46, 0.015, 0.88), m["ColorA"])
    parts.append(b)
    for p in parts:
        if not p.data.uv_layers:
            bpy.context.view_layer.update()
            world_uv(p)
    return parts


def takilar_kale():
    """Uchisar benzeri kale kayasi: devasa tuf kutle, ic ice oyuklar."""
    m = mats()
    H = 62.0
    prof = [(-3, 60), (0, 56), (10, 46), (22, 36), (34, 30), (46, 22), (56, 13), (62, 5), (64, 0.8)]
    rock = displaced_lathe("kale", prof, m["Plaster"], 77, seg=320, rings=260, disp=0.09, strata=1.2)
    world_uv(rock)
    parts = [rock]
    rnd = random.Random(7)
    zs = [p[0] for p in prof]
    rs = [p[1] for p in prof]
    for k in range(110):
        ang = rnd.uniform(0, 2 * math.pi)
        z = rnd.uniform(4, H * 0.86)
        r = float(np.interp(z, zs, rs))
        x, y = math.cos(ang) * r, math.sin(ang) * r
        s = rnd.uniform(0.9, 1.7)
        parts.append(C.box("oyuk", (x, y, z), (s, 1.4, s * 1.5), m["Dark"], rot=(0, 0, ang + math.pi / 2)))
    # Tepede kucuk bayrak dirsegi
    for p in parts[1:]:
        world_uv(p)
    return parts


def duvar_bag():
    """Bag kenari kuru taş duvar: 6 m."""
    m = mats()
    parts = []
    rnd = random.Random(5)
    for k in range(60):
        x, z = rnd.uniform(-3, 3), rnd.uniform(0.1, 0.95)
        s = rnd.uniform(0.28, 0.52)
        parts.append(C.box("tas", (x, rnd.uniform(-0.12, 0.12), z * (1.05 - abs(x) * 0.03)), (s, 0.5, s * 0.7), m["StoneWall"], rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.15, 0.15))))
    for p in parts:
        world_uv(p)
    return parts


def uzum_sira():
    """Bag sirasi: asma kazik ve yaprakli sira (uzum). 8 m."""
    m = mats()
    parts = []
    rnd = random.Random(9)
    for x in (-4, -1.34, 1.33, 4):
        parts.append(C.cylinder("post", (x, 0, 0), (x, 0, 1.3), 0.03, m["Wood"], 8))
    parts.append(C.cylinder("wire", (-4, 0, 0.9), (4, 0, 0.9), 0.006, m["Dark"], 5))
    # Yaprak kumesi: kucuk diskler
    verts, faces = [], []
    cols = []
    for k in range(1200):
        x = rnd.uniform(-3.9, 3.9)
        y = rnd.gauss(0, 0.22)
        z = rnd.uniform(0.35, 1.25)
        s = rnd.uniform(0.045, 0.09)
        ax = rnd.uniform(0, 6.28)
        d = Vector((math.cos(ax), math.sin(ax), rnd.uniform(-0.5, 0.5))).normalized()
        u = Vector((0, 0, 1)).cross(d).normalized()
        w = d.cross(u)
        base = len(verts)
        verts += [tuple(Vector((x, y, z)) + u * s), tuple(Vector((x, y, z)) + w * s), tuple(Vector((x, y, z)) - u * s), tuple(Vector((x, y, z)) - w * s)]
        faces.append((base, base + 1, base + 2, base + 3))
        g = rnd.uniform(0.55, 1.0)
        cols.append((0.20 * g, 0.34 * g, 0.08 * g, 1))
    f = C.from_pydata("leaves", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(4):
            f.data.color_attributes["Col"].data[i * 4 + t].color = c
    world_uv(f)
    parts.append(f)
    for p in parts:
        if not p.data.uv_layers:
            bpy.context.view_layer.update()
            world_uv(p)
    return parts


def kavak(seed, H=18.0):
    """Kavak: dik, dar, Kapadokya vadilerinin tipik agaci. Yaprak bulutu disk kartlar."""
    m = mats()
    rnd = random.Random(seed)
    parts = [C.tube("trunk", [(0, 0, 0), (0.03, 0.03, H * 0.5), (0, 0, H * 0.96)], [0.2, 0.11, 0.015], m["Wood"], 12)]
    world_uv(parts[0])
    verts, faces, cols = [], [], []
    N = 3200
    for k in range(N):
        z = rnd.uniform(0.11, 0.99) * H
        t = z / H
        R = 1.5 * math.sin(math.pi * min(1, t * 1.06)) ** 0.8
        a = rnd.uniform(0, 6.28)
        r = R * rnd.random() ** 0.45
        c = Vector((math.cos(a) * r, math.sin(a) * r, z))
        s = rnd.uniform(0.085, 0.16)
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.5, 0.8))).normalized()
        u = Vector((0, 0, 1)).cross(d).normalized()
        w = d.cross(u)
        b = len(verts)
        verts += [tuple(c + u * s), tuple(c + w * s * 1.2), tuple(c - u * s), tuple(c - w * s * 1.2)]
        faces.append((b, b + 1, b + 2, b + 3))
        g = rnd.uniform(0.6, 1.0)
        shade = 0.55 + 0.45 * (r / max(R, 0.01))
        cols.append((0.24 * g * shade, 0.34 * g * shade, 0.10 * g * shade, 1))
    f = C.from_pydata("leaves", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(4):
            f.data.color_attributes["Col"].data[i * 4 + t].color = c
    world_uv(f)
    parts.append(f)
    return parts


def kayisi(seed):
    """Kisa, yayvan meyve agaci."""
    m = mats()
    rnd = random.Random(seed)
    parts = [C.tube("trunk", [(0, 0, 0), (0.05, 0.02, 0.9), (-0.05, 0.08, 1.7)], [0.14, 0.1, 0.07], m["Wood"], 10)]
    world_uv(parts[0])
    for k in range(5):
        a = k * 1.3 + rnd.random()
        tip = Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, 2.4 + rnd.random() * 0.9))
        parts.append(C.tube("branch", [(0, 0, 1.1), tuple(tip * 0.6), tuple(tip)], [0.07, 0.04, 0.012], m["Wood"], 6))
        world_uv(parts[-1])
    verts, faces, cols = [], [], []
    for k in range(3400):
        a = rnd.uniform(0, 6.28)
        e = rnd.uniform(-0.45, 1.0)
        r = rnd.uniform(0.2, 1.0) ** 0.5
        c = Vector((math.cos(a) * math.cos(e) * 2.5 * r, math.sin(a) * math.cos(e) * 2.5 * r, 2.65 + math.sin(e) * 1.65 * r))
        s = rnd.uniform(0.06, 0.13)
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 1))).normalized()
        u = Vector((0, 0, 1)).cross(d).normalized()
        w = d.cross(u)
        b = len(verts)
        verts += [tuple(c + u * s), tuple(c + w * s * 1.2), tuple(c - u * s), tuple(c - w * s * 1.2)]
        faces.append((b, b + 1, b + 2, b + 3))
        g = rnd.uniform(0.55, 1.0)
        fruit = rnd.random() < 0.05
        col = (0.92, 0.5, 0.1, 1) if fruit else (0.17 * g, 0.31 * g, 0.08 * g, 1)
        cols.append(col)
    f = C.from_pydata("leaves", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(4):
            f.data.color_attributes["Col"].data[i * 4 + t].color = c
    world_uv(f)
    parts.append(f)
    return parts


def cali(seed):
    """Kuru bozkir cali/ot kumesi."""
    m = mats()
    rnd = random.Random(seed)
    verts, faces, cols = [], [], []
    for k in range(120):
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(0, 0.5)
        h = rnd.uniform(0.25, 0.7)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        tip = base + Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), h))
        w = rnd.uniform(0.012, 0.03)
        side = Vector((math.cos(a + 1.57), math.sin(a + 1.57), 0)) * w
        b = len(verts)
        verts += [tuple(base - side), tuple(base + side), tuple(tip)]
        faces.append((b, b + 2, b + 1))
        v = rnd.uniform(0.7, 1)
        cols.append((0.30 * v, 0.27 * v, 0.14 * v, 1))
    f = C.from_pydata("cali", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(3):
            f.data.color_attributes["Col"].data[i * 3 + t].color = c
    world_uv(f)
    return [f]


def kask():
    """Yol bisikleti kaski ve gozluk. Bas kemigi merkezli (Y one bakacak sekilde UE'de doner)."""
    m = {"Helmet": C.mat("Helmet"), "Vent": C.mat("Vent"), "Glass": C.mat("Glass")}
    verts, faces = [], []
    seg, rings = 48, 24
    for j in range(rings + 1):
        v = j / rings
        el = (v - 0.0) * math.pi * 0.55
        for i in range(seg):
            a = 2 * math.pi * i / seg
            r = math.cos(el)
            x = r * math.cos(a)
            y = r * math.sin(a)
            z = math.sin(el)
            # Kusa: boylamasina one-arkaya uzatilmis, arkasi dusuk
            sx = 0.128 * (1.0 + 0.08 * max(0, -x))
            sy = 0.102
            sz = 0.095
            ridge = 0.004 * abs(math.sin(a * 8)) * (1 - v)
            verts.append((x * (sx + ridge), y * (sy + ridge), z * (sz + ridge) + 0.05 - 0.018 * max(0, -x)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            c = (j + 1) * seg + (i + 1) % seg
            d = (j + 1) * seg + i
            faces.append((a, b, c, d))
    faces.append(tuple(rings * seg + i for i in range(seg)))
    h = C.from_pydata("kask", verts, faces, m["Helmet"])
    world_uv(h)
    parts = [h]
    # Havalandirma
    for k in range(5):
        y = (k - 2) * 0.034
        parts.append(C.box("vent", (0.02, y, 0.142), (0.15, 0.012, 0.012), m["Vent"], rot=(0, 0.1, 0)))
    C.export_kmsh(parts, "Helmet.kmsh", {"Helmet": 0, "Vent": 1, "Glass": 2})
    for p in parts:
        bpy.data.objects.remove(p)
    # Gozluk
    glass = []
    for s in (-1, 1):
        b = C.box("lens", (0.092, s * 0.036, 0.0), (0.012, 0.058, 0.034), m["Glass"])
        b.data.transform(b.matrix_world)
        b.matrix_world = Matrix.Identity(4)
        world_uv(b)
        glass.append(b)
        glass.append(C.cylinder("arm", (0.088, s * 0.07, 0.008), (-0.03, s * 0.09, 0.012), 0.002, m["Vent"], 5))
    world_uv(glass[1])
    world_uv(glass[3])
    C.export_kmsh(glass, "Glasses.kmsh", {"Helmet": 0, "Vent": 1, "Glass": 2})


# ------------------------------------------------------------- uretim listesi
def export(name, parts, slots=SLOTS_ARCH):
    C.export_kmsh(parts, name + ".kmsh", slots)
    for p in parts:
        bpy.data.objects.remove(p)


C.clear_scene()
for i, (H, br, cr, ch) in enumerate([(14, 4.4, 1.9, 1.9), (20, 5.2, 2.3, 2.3), (11, 3.6, 1.5, 1.3), (26, 6.4, 2.7, 2.7), (9, 3.2, 1.6, 1.2)]):
    export(f"Chimney{i}", fairy_chimney(i, 40 + i * 9, H, br, cr, ch))
for i, (f, lx, ly) in enumerate([(2, 9, 7), (3, 11, 8), (2, 7.5, 6.5), (3, 8.5, 9)]):
    export(f"Konak{i}", konak(i, 21 + i * 3, f, lx, ly))
for i in range(3):
    export(f"Magara{i}", magara_ev(60 + i))
export("Cami", cami())
export("Kervansaray", kervansaray())
export("Kopru", kopru())
export("Cesme", cesme())
for i in range(3):
    export(f"Tezgah{i}", tente_stall(i, 80 + i))
export("CayMasa", cay_masa())
BALLOON_PAL = [
    [(0.72, 0.03, 0.03), (0.92, 0.80, 0.45)],
    [(0.06, 0.18, 0.55), (0.92, 0.62, 0.10)],
    [(0.12, 0.45, 0.42), (0.92, 0.88, 0.7)],
    [(0.80, 0.30, 0.05), (0.30, 0.04, 0.25)],
    [(0.92, 0.62, 0.10), (0.65, 0.05, 0.10)],
]
for i, pal in enumerate(BALLOON_PAL):
    export(f"Balon{i}", balloon(i, pal))
export("Bayrak", bayrak())
export("Flama", flama_ipi())
export("Bariyer", bariyer())
export("KaleKaya", takilar_kale())
export("TasDuvar", duvar_bag())
export("BagSira", uzum_sira())
for i in range(2):
    export(f"Kavak{i}", kavak(100 + i, 17 + i * 3))
for i in range(2):
    export(f"Kayisi{i}", kayisi(200 + i))
for i in range(3):
    export(f"Cali{i}", cali(300 + i))
kask()
print("TUM PROPLAR TAMAM")
