"""Parametrik yol bisikleti. Gorunen olculer gercek 56 cm gerceve geometrisine yakindir.

Bisiklet yerel uzayi: orijin yerde, orta gobek altinda. +X ileri, +Z yukari, metre.
Cikti parcalari ve pivotlari (KapadokyaRider.cpp ile ayni olmali):
  BikeFrame  orijin (0,0,0)
  BikeSteer  pivot HEAD_PIVOT
  BikeWheel  pivot aks merkezi
  BikeCrank  pivot BB
  BikePedal  pivot pedal aksi
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

import bl_common as C

C.clear_scene()
PAINT = C.mat("Paint", (0.75, 0.03, 0.05, 1), 0.28, 0.0)
CARBON = C.mat("Carbon", (0.015, 0.015, 0.017, 1), 0.34)
METAL = C.mat("Metal", (0.75, 0.75, 0.76, 1), 0.28, 1.0)
RUBBER = C.mat("Rubber", (0.018, 0.018, 0.018, 1), 0.78)
SLOTS = {"Paint": 0, "Carbon": 1, "Metal": 2, "Rubber": 3}

R_WHEEL = 0.340
REAR = Vector((-0.405, 0, R_WHEEL))
FRONT = Vector((0.585, 0, R_WHEEL))
BB = Vector((0, 0, 0.268))
SEAT_TOP = Vector((-0.155, 0, 0.80))
HEAD_TOP = Vector((0.385, 0, 0.865))
HEAD_BOT = Vector((0.430, 0, 0.715))
SADDLE = Vector((-0.205, 0, 0.965))
HEAD_PIVOT = HEAD_BOT


def side(p, y):
    return Vector((p[0], y, p[2]))


# ------------------------------------------------------------ gerceve
frame = []
frame.append(C.tube("down", [HEAD_BOT + Vector((-0.012, 0, 0.012)), (HEAD_BOT * 0.62 + BB * 0.38), BB + Vector((0.01, 0, 0.012))], [0.024, 0.027, 0.031], PAINT))
frame.append(C.tube("top", [HEAD_TOP + Vector((-0.015, 0, -0.018)), (HEAD_TOP * 0.5 + SEAT_TOP * 0.5) + Vector((0, 0, -0.006)), SEAT_TOP + Vector((0, 0, -0.022))], [0.019, 0.016, 0.014], PAINT))
frame.append(C.tube("seat", [BB + Vector((-0.002, 0, 0.012)), BB * 0.55 + SEAT_TOP * 0.45 + Vector((0.012, 0, 0)), SEAT_TOP], [0.024, 0.02, 0.017], PAINT))
frame.append(C.cylinder("head", HEAD_BOT + Vector((0.004, 0, -0.012)), HEAD_TOP + Vector((-0.002, 0, 0.008)), 0.0275, PAINT, 32, 0.022))
frame.append(C.cylinder("bbshell", BB + Vector((0, -0.038, 0)), BB + Vector((0, 0.038, 0)), 0.024, CARBON, 32))
for y0, y1 in ((-0.03, -0.066), (0.03, 0.066)):
    frame.append(C.tube("chain", [side(BB, y0) + Vector((-0.02, 0, 0)), side((BB + REAR) * 0.5, (y0 + y1) / 2), side(REAR, y1)], [0.014, 0.011, 0.009], PAINT))
    frame.append(C.tube("stay", [side(SEAT_TOP + Vector((0.01, 0, -0.07)), y0 * 0.55), side(SEAT_TOP * 0.45 + REAR * 0.55, (y0 + y1) / 2), side(REAR, y1)], [0.010, 0.008, 0.008], PAINT))
    frame.append(C.cylinder("drop", side(REAR, y1) + Vector((0, 0, -0.012)), side(REAR, y1) + Vector((0, 0, 0.012)), 0.012, METAL, 12))
# Sele borusu ve sele
frame.append(C.cylinder("seatpost", SEAT_TOP, SADDLE + Vector((0.015, 0, -0.012)), 0.0135, CARBON, 20))
frame.append(C.cylinder("clamp", SEAT_TOP + Vector((0, 0, -0.008)), SEAT_TOP + Vector((0, 0, 0.012)), 0.019, METAL, 20))
# Sele: boyuna kesitli lofta benzer yuzey
sv, sf = [], []
sections = [(-0.13, 0.068, 0.012), (-0.09, 0.070, 0.022), (-0.04, 0.058, 0.024), (0.02, 0.032, 0.022), (0.08, 0.021, 0.021), (0.135, 0.016, 0.018), (0.15, 0.008, 0.008)]
ring = 18
for x, w, h in sections:
    for k in range(ring):
        t = 2 * math.pi * k / ring
        # Ust taraf bombeli, alt taraf ice bukuk
        z = (math.sin(t) * h) if math.sin(t) > 0 else (math.sin(t) * h * 0.4)
        sv.append((SADDLE.x + x, math.cos(t) * w, SADDLE.z + z - 0.03 * (abs(x) * 2) ** 2))
for i in range(len(sections) - 1):
    for k in range(ring):
        a = i * ring + k
        b = i * ring + (k + 1) % ring
        sf.append((a, a + ring, b + ring, b))
sf.append(tuple(k for k in reversed(range(ring))))
sf.append(tuple((len(sections) - 1) * ring + k for k in range(ring)))
frame.append(C.from_pydata("saddle", sv, sf, RUBBER))
for y in (-0.02, 0.02):
    frame.append(C.tube("rail", [SADDLE + Vector((-0.07, y, -0.015)), SADDLE + Vector((0, y, -0.04)), SADDLE + Vector((0.08, y * 0.4, -0.015))], 0.0035, METAL, 8))
# Arka vites: kaset
for i, teeth in enumerate([11, 12, 13, 14, 15, 16, 17, 19, 21, 24, 27, 30]):
    rr = teeth * 0.00254 / math.pi * 1.0
    y = -0.060 + i * 0.0037
    frame.append(C.cylinder("sprocket", REAR + Vector((0, y - 0.0009, 0)), REAR + Vector((0, y + 0.0009, 0)), rr, METAL, max(teeth * 2, 20)))
# Vites degistirici
hanger = REAR + Vector((0.005, -0.070, -0.04))
frame.append(C.cylinder("der1", hanger, hanger + Vector((-0.012, -0.002, -0.05)), 0.009, CARBON, 12))
jock = hanger + Vector((0.0, -0.002, -0.075))
idler = jock + Vector((0.035, 0, -0.06))
frame.append(C.cylinder("cage", jock, idler, 0.006, CARBON, 8))
for pulley in (jock, idler):
    frame.append(C.cylinder("pulley", pulley + Vector((0, -0.004, 0)), pulley + Vector((0, 0.004, 0)), 0.016, METAL, 20))
# Zincir: ust ve alt kol
ring_r = 52 * 0.0127 / (2 * math.pi)
chain_y = -0.045
top_a = BB + Vector((0, chain_y, ring_r))
top_b = REAR + Vector((0, chain_y, 0.045))
low_a = BB + Vector((0, chain_y, -ring_r))
n_links = 28
for (a, b) in ((top_a, top_b), (low_a, jock + Vector((0, 0, -0.012))), (jock + Vector((0.01, 0, 0.006)), REAR + Vector((-0.04, chain_y, -0.03)))):
    frame.append(C.cylinder("chainrun", a + Vector((0, -0.002, 0)), b + Vector((0, -0.002, 0)), 0.0042, METAL, 8))
# Su matara kafesi ve matara
bot_a = (HEAD_BOT * 0.42 + BB * 0.58) + Vector((-0.045, 0, 0.018))
bot_b = bot_a + (HEAD_BOT - BB).normalized() * 0.19
frame.append(C.cylinder("bottle", bot_a, bot_b, 0.036, CARBON, 24))
frame.append(C.cylinder("bottlecap", bot_b, bot_b + (HEAD_BOT - BB).normalized() * 0.022, 0.024, METAL, 16, 0.012))
# Arka fren
frame.append(C.cylinder("rbrake", SEAT_TOP * 0.34 + REAR * 0.66 + Vector((0, -0.03, 0.0)), SEAT_TOP * 0.34 + REAR * 0.66 + Vector((0, 0.03, 0.0)), 0.01, METAL, 12))
C.export_kmsh(frame, "BikeFrame.kmsh", SLOTS)

# ------------------------------------------------------------ gidon/catal
steer = []
crown = HEAD_BOT + Vector((0.008, 0, -0.018))
fork_mid = crown * 0.48 + FRONT * 0.52 + Vector((-0.012, 0, 0))
for y, yc in ((-0.056, -0.026), (0.056, 0.026)):
    steer.append(C.tube("fork", [side(crown, yc), side(fork_mid, (y + yc) / 1.8), side(FRONT, y)], [0.02, 0.015, 0.008], PAINT))
steer.append(C.cylinder("crown", side(crown, -0.032), side(crown, 0.032), 0.021, PAINT, 20))
stem_base = HEAD_TOP + Vector((-0.004, 0, 0.022))
bar_c = stem_base + Vector((0.098, 0, 0.018))
steer.append(C.cylinder("steerer", HEAD_TOP, stem_base + Vector((-0.006, 0, 0.022)), 0.016, CARBON, 20))
steer.append(C.tube("stem", [stem_base, bar_c], 0.017, CARBON, 20))
steer.append(C.cylinder("clampbar", bar_c + Vector((0, -0.024, 0)), bar_c + Vector((0, 0.024, 0)), 0.021, CARBON, 20))
width = 0.205
for s in (-1, 1):
    pts = [
        bar_c,
        bar_c + Vector((0.004, s * 0.11, 0.001)),
        bar_c + Vector((0.042, s * width * 0.94, -0.002)),
        bar_c + Vector((0.098, s * width, -0.034)),
        bar_c + Vector((0.098, s * width, -0.094)),
        bar_c + Vector((0.042, s * width, -0.128)),
        bar_c + Vector((-0.050, s * width, -0.132)),
    ]
    steer.append(C.tube("bar", pts, 0.0125, CARBON, 16, 18))
    # Vites/fren kolu
    hood = bar_c + Vector((0.11, s * width, -0.012))
    steer.append(C.tube("hood", [bar_c + Vector((0.085, s * width, -0.028)), hood, hood + Vector((0.035, 0, 0.022))], [0.017, 0.019, 0.016], RUBBER, 16))
    steer.append(C.tube("lever", [hood + Vector((0.022, 0, 0.006)), hood + Vector((0.04, 0, -0.06)), hood + Vector((0.015, 0, -0.12))], [0.007, 0.006, 0.0045], METAL, 12))
# On fren
steer.append(C.cylinder("fbrake", crown + Vector((0.025, -0.03, -0.04)), crown + Vector((0.025, 0.03, -0.04)), 0.011, METAL, 12))
C.export_kmsh(steer, "BikeSteer.kmsh", SLOTS, origin=tuple(HEAD_PIVOT))

# ------------------------------------------------------------ teker (pivot aks)
wheel = []
tire_r = 0.0135
rim_out = R_WHEEL - 2 * tire_r + 0.002
rim_in = rim_out - 0.045
# Lastik: dis yuzeyde hafif desen
pv, pf = [], []
segs, ring = 256, 20
for s in range(segs):
    t = 2 * math.pi * s / segs
    tread = 0.0003 * math.sin(t * 90)
    for k in range(ring):
        a = 2 * math.pi * k / ring
        r = R_WHEEL - tire_r + math.cos(a) * (tire_r + tread * max(0, math.cos(a)))
        pv.append((r * math.cos(t), math.sin(a) * tire_r, r * math.sin(t)))
for s in range(segs):
    s2 = (s + 1) % segs
    for k in range(ring):
        k2 = (k + 1) % ring
        pf.append((s * ring + k, s * ring + k2, s2 * ring + k2, s2 * ring + k))
wheel.append(C.from_pydata("tire", pv, pf, RUBBER))
# Jant profili
wheel.append(C.lathe("rim", [(rim_in, 0.0), (rim_in + 0.004, 0.006), (rim_out - 0.012, 0.0105), (rim_out, 0.0115), (rim_out, -0.0115), (rim_out - 0.012, -0.0105), (rim_in + 0.004, -0.006), (rim_in, 0.0)], CARBON, segments=128))
wheel.append(C.lathe("braketrack", [(rim_out - 0.002, 0.0118), (rim_out - 0.012, 0.0108)], METAL, segments=128))
wheel.append(C.lathe("braketrack2", [(rim_out - 0.012, -0.0108), (rim_out - 0.002, -0.0118)], METAL, segments=128))
# Gobek
wheel.append(C.lathe("hub", [(0.006, -0.05), (0.018, -0.042), (0.026, -0.036), (0.013, -0.02), (0.012, 0.02), (0.026, 0.036), (0.018, 0.042), (0.006, 0.05)], METAL, segments=32))
# Teller: duz + capraz
for i in range(24):
    side_sign = 1 if i % 2 == 0 else -1
    ang = 2 * math.pi * i / 24
    cross = 0.5 * (1 if (i // 2) % 2 == 0 else -1)
    hub_a = ang + cross
    p_hub = Vector((0.024 * math.cos(hub_a), side_sign * 0.034, 0.024 * math.sin(hub_a)))
    p_rim = Vector((rim_in * math.cos(ang), side_sign * 0.003, rim_in * math.sin(ang)))
    wheel.append(C.cylinder("spoke", p_hub, p_rim, 0.00105, METAL, 5))
C.export_kmsh(wheel, "BikeWheel.kmsh", SLOTS)

# ------------------------------------------------------------ krank (pivot BB)
crank = []
CRANK_LEN = 0.1725
crank.append(C.cylinder("axle", (0, -0.068, 0), (0, 0.068, 0), 0.012, METAL, 20))
# Disli zincir halkasi
rv, rf = [], []
for teeth, radius, y, thick in ((52, ring_r, -0.045, 0.0024), (36, 36 * 0.0127 / (2 * math.pi), -0.038, 0.0024)):
    base = len(rv)
    pts = []
    for t in range(teeth * 2):
        a = 2 * math.pi * t / (teeth * 2)
        r = radius + (0.0038 if t % 2 == 0 else -0.001)
        pts.append((r * math.cos(a), r * math.sin(a)))
    inner = radius * 0.72
    n = len(pts)
    for yy in (y - thick, y + thick):
        for (x, z) in pts:
            rv.append((x, yy, z))
        for k in range(n):
            a = 2 * math.pi * k / n
            rv.append((inner * math.cos(a), yy, inner * math.sin(a)))
    o0, i0, o1, i1 = base, base + n, base + 2 * n, base + 3 * n
    for k in range(n):
        k2 = (k + 1) % n
        rf.append((o0 + k, i0 + k, i0 + k2, o0 + k2))
        rf.append((o1 + k2, i1 + k2, i1 + k, o1 + k))
        rf.append((o0 + k2, o1 + k2, o1 + k, o0 + k))
        rf.append((i0 + k, i1 + k, i1 + k2, i0 + k2))
crank.append(C.from_pydata("rings", rv, rf, METAL, smooth=False))
for i in range(4):
    a = 2 * math.pi * (i + 0.5) / 4
    crank.append(C.tube("spider", [Vector((0.01 * math.cos(a), -0.05, 0.01 * math.sin(a))), Vector((ring_r * 0.75 * math.cos(a), -0.044, ring_r * 0.75 * math.sin(a)))], [0.009, 0.006], CARBON, 12))
# Kollar: Y- tarafi saga-asagi, Y+ tarafi yukari; aci 0'da sag pedal ileri
for sgn, rot in ((-1, 0.0), (1, math.pi)):
    tip = Vector((CRANK_LEN * math.cos(rot), sgn * 0.078, CRANK_LEN * math.sin(rot)))
    crank.append(C.tube("arm", [Vector((0, sgn * 0.066, 0)), tip], [0.016, 0.010], CARBON, 16))
C.export_kmsh(crank, "BikeCrank.kmsh", SLOTS)

# ------------------------------------------------------------ pedal (pivot aks)
ped = [C.box("body", (0, 0, 0), (0.088, 0.064, 0.016), CARBON), C.cylinder("axle", (0, -0.035, 0), (0, 0.035, 0), 0.005, METAL, 10)]
C.export_kmsh(ped, "BikePedal.kmsh", SLOTS)

# ------------------------------------------------------------ onizleme: tam montaj
for o in list(bpy.data.objects):
    pass
assembled = []
def clone(objs, offset):
    for o in objs:
        c = o.copy()
        c.location = o.location + Vector(offset)
        bpy.context.scene.collection.objects.link(c)

# Sadece onizleme icin kopyalar; dosyaya yazilmaz
for o in wheel:
    o.location = Vector(REAR)
clone(wheel, tuple(FRONT - REAR))
for o in crank:
    o.location = Vector(BB)
if len(sys.argv) > 1 and sys.argv[-1].endswith(".png"):
    C.preview(sys.argv[-1])
