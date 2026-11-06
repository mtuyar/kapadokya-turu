"""Baslangic kemeri, seyirci figurleri, kayalar."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Matrix, Vector

import bl_common as C

C.clear_scene()
exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bl_props.py"), encoding="utf8").read().split("# ------------------------------------------------------------- uretim listesi")[0], "bl_props_defs", "exec"))


def export(name, parts, slots=SLOTS_ARCH):
    C.export_kmsh(parts, name + ".kmsh", slots)
    for p in parts:
        bpy.data.objects.remove(p)


def kemer():
    """Yol ustu tahta/metal kemer: ayaklar yolun disinda, ust panel UE tarafinda yazi alir."""
    m = mats()
    parts = []
    half = 7.6
    H = 6.2
    for s in (-1, 1):
        parts.append(wall_box("post", (0, s * half, H / 2), (0.5, 0.5, H), m["Dark"]))
        parts.append(wall_box("foot", (0, s * half, 0.3), (1.2, 1.2, 0.6), m["Stone"]))
    parts.append(wall_box("banner", (0, 0, H - 0.55), (0.16, half * 2 + 0.5, 1.3), m["ColorA"]))
    # Dama: bitis cizgisi seridi, yola serili
    verts, faces, cols = [], [], []
    nx, ny = 4, 36
    sqx, sqy = 0.30, half * 1.1 / ny
    for j in range(nx):
        for i in range(ny):
            x0 = -sqx * nx / 2 + j * sqx
            y0 = -half * 0.55 + i * sqy
            b = len(verts)
            z = 0.045
            verts += [(x0, y0, z), (x0 + sqx, y0, z), (x0 + sqx, y0 + sqy, z), (x0, y0 + sqy, z)]
            faces.append((b, b + 1, b + 2, b + 3))
            cols.append((0.92, 0.92, 0.9, 1) if (i + j) % 2 == 0 else (0.02, 0.02, 0.02, 1))
    f = C.from_pydata("dama", verts, faces, m["ColorB"], smooth=False)
    f.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    for i, c in enumerate(cols):
        for t in range(4):
            f.data.color_attributes["Col"].data[i * 4 + t].color = c
    world_uv(f)
    parts.append(f)
    return parts


def seyirci(seed):
    """Dolgu figur: uzaktan okunur bicimde kalabalik, gercek insan degil."""
    m = mats()
    r = random.Random(seed)
    skin = r.choice([(0.55, 0.36, 0.26), (0.62, 0.42, 0.31), (0.46, 0.29, 0.20)])
    top = r.choice([(0.55, 0.05, 0.05), (0.12, 0.2, 0.42), (0.75, 0.72, 0.65), (0.15, 0.32, 0.26), (0.5, 0.33, 0.1)])
    bot = r.choice([(0.05, 0.06, 0.09), (0.2, 0.2, 0.22), (0.3, 0.24, 0.17)])
    arms_up = seed % 2 == 0
    head_col = r.choice([skin, skin, (0.75, 0.12, 0.12), (0.1, 0.1, 0.12)])

    def paint(o, c):
        o.data.color_attributes.new("Col", "BYTE_COLOR", "POINT")
        for d in o.data.color_attributes["Col"].data:
            d.color = (*c, 1)
        return o

    parts = []
    for s in (-1, 1):
        parts.append(paint(C.cylinder("leg", (0, s * 0.1, 0.0), (0, s * 0.11, 0.84), 0.075, m["ColorB"], 10, 0.085), bot))
        hand = (0.05, s * 0.34, 1.9) if arms_up else (0.05, s * 0.29, 0.86)
        parts.append(paint(C.tube("arm", [(0, s * 0.21, 1.34), (0.05, s * 0.3, 1.5 if arms_up else 1.12), hand], [0.052, 0.045, 0.036], m["ColorB"], 8), top))
        parts.append(paint(C.cylinder("hand", hand, (hand[0], hand[1], hand[2] + (0.1 if arms_up else -0.1)), 0.04, m["ColorB"], 8), skin))
    torso = C.lathe("torso", [(0.12, -0.3), (0.2, -0.2), (0.21, 0.0), (0.2, 0.2), (0.12, 0.3)], m["ColorB"], segments=16)
    torso.rotation_euler = (math.radians(90), 0, 0)
    torso.location = (0, 0, 1.12)
    parts.append(paint(torso, top))
    head = C.lathe("head", [(0.01, -0.12), (0.095, -0.08), (0.11, 0.0), (0.09, 0.09), (0.01, 0.12)], m["ColorB"], segments=16)
    head.rotation_euler = (math.radians(90), 0, 0)
    head.location = (0, 0, 1.6)
    parts.append(paint(head, head_col))
    for p in parts:
        bpy.context.view_layer.update()
        world_uv(p)
    return parts


def kaya(seed):
    m = mats()
    prof = [(-0.4, 0.5), (0.0, 1.0), (0.45, 0.85), (0.85, 0.5), (1.05, 0.08)]
    o = displaced_lathe("kaya", prof, m["Plaster"], seed, seg=48, rings=26, disp=0.42, strata=0.06)
    world_uv(o)
    return [o]


export("Kemer", kemer())
for i in range(4):
    export(f"Seyirci{i}", seyirci(i * 7 + (i % 2)))
for i in range(3):
    export(f"Kaya{i}", kaya(500 + i))
print("EKSTRA TAMAM")
