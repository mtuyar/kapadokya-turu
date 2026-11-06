"""Tum yerlesimleri uretir: Content/Kapadokya/Data/placements.json.

Kurallar: yol koridoruna girmez, bolgeye gore kultur peyzaji degisir. Sabit tohum: harita tekrarlanabilir.
"""
import json
import math
import os

import numpy as np

import route as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = np.load(os.path.join(ROOT, "RawAssets", "world.npz"))
H, D, xs, ys, rock, grass, lake, river = W["H"], W["D"], W["xs"], W["ys"], W["rock"], W["grass"], W["lake"], W["river"]
P, zone, S, L = R.build()
T, K, GR = R.metrics(P)
N = np.stack([-T[:, 1], T[:, 0]], 1)
HALF = np.array([R.ZONE_HALFWIDTH[z] for z in zone])
ZI = np.array(zone)
WATER = -50.0
rng = np.random.default_rng(1453)
cell = xs[1] - xs[0]
out = {}


def sample(arr, x, y):
    i = np.clip(((x - xs[0]) / cell).astype(int), 0, len(xs) - 1)
    j = np.clip(((y - ys[0]) / cell).astype(int), 0, len(ys) - 1)
    return arr[j, i]


def h1(x, y):
    return float(sample(H, np.array([x]), np.array([y]))[0])


def d1(x, y):
    return float(sample(D, np.array([x]), np.array([y]))[0])


def add(mesh, x, y, z, yaw, scale=1.0, collide=False, cull=1200.0):
    e = out.setdefault(mesh, {"collide": collide, "cull": cull, "t": []})
    e["t"] += [round(float(x), 2), round(float(y), 2), round(float(z), 2), round(float(yaw), 1), round(float(scale), 3)]


def yaw_front_to(dx, dy):
    """Modellerin on yuzu UE +Y'ye bakar. Verilen yone cevirir (derece)."""
    return math.degrees(math.atan2(-dx, dy))


def footprint_ok(x, y, yaw, lx, ly, margin=1.5):
    a = math.radians(yaw)
    cs, sn = math.cos(a), math.sin(a)
    for u in np.linspace(-lx / 2, lx / 2, 5):
        for v in np.linspace(-ly / 2, ly / 2, 5):
            px = x + u * cs - v * sn
            py = y + u * sn + v * cs
            idx = np.argmin((P[:, 0] - px) ** 2 + (P[:, 1] - py) ** 2)
            if math.hypot(P[idx, 0] - px, P[idx, 1] - py) < HALF[idx] + margin:
                return False
    return True


def zone_idx(*names):
    return np.where(np.isin(ZI, names))[0]


# ----------------------------------------------------- Carsi: baslangic/bitis, yapilar
START_S = 360.0
start_i = int(np.argmin(np.abs(S - START_S)))
sx, sy, sz = P[start_i]
add("Kemer", sx, sy, sz, math.degrees(math.atan2(T[start_i, 1], T[start_i, 0])), 1.0, cull=0.0)

carsi = zone_idx(R.CARSI)
placed_build = []
for side in (1, -1):
    s_pos = S[carsi[0]] + 12.0
    while s_pos < S[carsi[-1]] - 8:
        i = int(np.argmin(np.abs(S - s_pos)))
        kind = rng.integers(0, 4)
        lx, ly = [(9, 7), (11, 8), (7.5, 6.5), (8.5, 9)][kind]
        off = HALF[i] + 7.0 + ly / 2
        x, y = P[i, :2] + N[i] * side * off
        yaw = yaw_front_to(-N[i, 0] * side, -N[i, 1] * side)
        # Cami yeri bos kalsin
        if abs(s_pos - 500) > 22 and footprint_ok(x, y, yaw, lx + 2, ly + 2, 2.5):
            add(f"Konak{kind}", x, y, P[i, 2] - 0.15, yaw, 1.0, collide=True, cull=2000.0)
            placed_build.append((x, y))
            # Arka sira: daha derin kasaba
            kind2 = rng.integers(0, 4)
            off2 = off + 13 + rng.uniform(0, 5)
            x2, y2 = P[i, :2] + N[i] * side * off2
            if footprint_ok(x2, y2, yaw, 11, 10, 3):
                add(f"Konak{kind2}", x2, y2, h1(x2, y2) - 0.2, yaw + rng.choice([0, 90, 180, 270]), 1.0, collide=True, cull=2000.0)
        s_pos += lx + rng.uniform(2.5, 5.5)
# Cami: meydan kuzeyinde, yola bakar
i = int(np.argmin(np.abs(S - 500)))
cx, cy = P[i, :2] + N[i] * -(HALF[i] + 19.0)
cyaw = yaw_front_to(N[i, 0], N[i, 1])
add("Cami", cx, cy, P[i, 2] - 0.15, cyaw, 1.0, collide=True, cull=0.0)
# Cay bahcesi ve cesme: meydan
for k in range(12):
    a = k * 2.399
    r = 2.5 + 0.9 * math.sqrt(k + 1)
    i2 = int(np.argmin(np.abs(S - 465)))
    x, y = P[i2, :2] + N[i2] * (HALF[i2] + 5.8 + rng.uniform(0, 1.5)) + T[i2, :2] * (k * 3.6 - 16)
    add("CayMasa", x, y, h1(x, y) + 0.02, rng.uniform(0, 360), 1.0, cull=200.0)
i3 = int(np.argmin(np.abs(S - 435)))
x, y = P[i3, :2] + N[i3] * -(HALF[i3] + 3.2)
add("Cesme", x, y, P[i3, 2] - 0.15, yaw_front_to(N[i3, 0], N[i3, 1]), 1.0, collide=True, cull=800.0)
# Tezgahlar
for side in (1, -1):
    s_pos = 120.0
    while s_pos < 680.0:
        if abs(s_pos - START_S) > 28 and abs(s_pos - 500) > 26:
            i = int(np.argmin(np.abs(S - s_pos)))
            x, y = P[i, :2] + N[i] * side * (HALF[i] + 3.4)
            add(f"Tezgah{rng.integers(0, 3)}", x, y, P[i, 2] - 0.15, yaw_front_to(-N[i, 0] * side, -N[i, 1] * side), 1.0, cull=500.0)
        s_pos += rng.uniform(7, 15)
# Bariyer + seyirci
ROADSIDE = [(START_S - 150, START_S + 110, 1.0), (S[zone_idx(R.KALE)[0]] - 110, S[zone_idx(R.KALE)[0]] + 45, 0.9)]
for a, b, dens in ROADSIDE:
    s_pos = a
    while s_pos < b:
        i = int(np.argmin(np.abs(S - s_pos)))
        for side in (1, -1):
            x, y = P[i, :2] + N[i] * side * (HALF[i] + 0.85)
            add("Bariyer", x, y, P[i, 2] - 0.15, math.degrees(math.atan2(T[i, 1], T[i, 0])) + (180 if side < 0 else 0), 1.0, collide=True, cull=350.0)
            for row in range(3):
                if rng.random() < dens * (0.82 - row * 0.2):
                    o2 = HALF[i] + 1.5 + row * 0.8 + rng.uniform(-0.15, 0.15)
                    x2, y2 = P[i, :2] + N[i] * side * o2 + T[i, :2] * rng.uniform(-1.1, 1.1)
                    add(f"Seyirci{rng.integers(0, 4)}", x2, y2, P[i, 2] - 0.15, yaw_front_to(-N[i, 0] * side, -N[i, 1] * side) + rng.uniform(-25, 25), rng.uniform(0.92, 1.06), cull=300.0)
        s_pos += 2.5
# Bayrak + flama
for s_pos in np.arange(100.0, 700.0, 22.0):
    i = int(np.argmin(np.abs(S - s_pos)))
    for side in (1, -1):
        x, y = P[i, :2] + N[i] * side * (HALF[i] + 1.1)
        add("Bayrak", x, y, P[i, 2] - 0.15, rng.uniform(70, 110), 1.0, collide=False, cull=700.0)
    x, y = P[i, :2]
    add("Flama", x, y, P[i, 2] + 7.2, math.degrees(math.atan2(N[i, 1], N[i, 0])), HALF[i] * 2.6 / 18.0, cull=500.0)

# ----------------------------------------------------- Kopru
br = zone_idx(R.KOPRU)
i_br = br[int(np.argmin(np.abs(P[br, 1] - 1010.0)))]
add("Kopru", P[i_br, 0], P[i_br, 1], P[i_br, 2] - 0.05, math.degrees(math.atan2(T[i_br, 1], T[i_br, 0])), 1.0, collide=False, cull=0.0)

# ----------------------------------------------------- Peribacalari
mask_v = np.isin(np.array(zone), [R.VADI, R.KOPRU, R.TIRMANIS])
pv = P[mask_v]
placed = []
for attempt in range(38000):
    k = rng.integers(0, len(pv))
    side = rng.choice([-1, 1])
    r = 14 + rng.exponential(55)
    a = rng.uniform(0, 2 * math.pi)
    x = pv[k, 0] + math.cos(a) * r
    y = pv[k, 1] + math.sin(a) * r
    dd = d1(x, y)
    if dd < 11 or dd > 240:
        continue
    if sample(lake, np.array([x]), np.array([y]))[0] > 0.1 or sample(river, np.array([x]), np.array([y]))[0] > 0.05:
        continue
    # Kumelenme: buyuk dalga
    clump = 0.5 + 0.5 * math.sin(x * 0.021 + 0.7) * math.cos(y * 0.017)
    if rng.random() > clump + 0.12:
        continue
    if any((x - qx) ** 2 + (y - qy) ** 2 < (qr + 5) ** 2 for qx, qy, qr in placed[-700:]):
        continue
    v = rng.integers(0, 5)
    base_r = [4.4, 5.2, 3.6, 6.4, 3.2][v]
    s = rng.uniform(0.72, 1.35) * (0.8 if dd < 30 else 1.0)
    if len(placed) > 620:
        break
    placed.append((x, y, base_r * s))
    add(f"Chimney{v}", x, y, h1(x, y) - 0.8, rng.uniform(0, 360), s, collide=True, cull=2800.0)
print("peribacasi", len(placed))

# Magara evler: tirmanista yol kenarinda
for idx in zone_idx(R.TIRMANIS)[::95]:
    side = rng.choice([-1, 1])
    off = HALF[idx] + 20 + rng.uniform(0, 12)
    x, y = P[idx, :2] + N[idx] * side * off
    if d1(x, y) > 15 and sample(lake, np.array([x]), np.array([y]))[0] < 0.1:
        add(f"Magara{rng.integers(0, 3)}", x, y, h1(x, y) - 1.0, yaw_front_to(-N[idx, 0] * side, -N[idx, 1] * side), rng.uniform(0.9, 1.3), collide=True, cull=2500.0)

# Kale kaya: kuzeybati
kx, ky = -70.0, 1520.0
add("KaleKaya", kx, ky, h1(kx, ky) - 15.0, 30.0, 1.0, collide=True, cull=0.0)

# ----------------------------------------------------- Kervansaray
kv = zone_idx(R.KERVAN)
i_k = kv[len(kv) // 2]
side = 1 if d1(*(P[i_k, :2] + N[i_k] * 60)) > d1(*(P[i_k, :2] - N[i_k] * 60)) else -1
kxy = P[i_k, :2] + N[i_k] * side * (HALF[i_k] + 26.0)
add("Kervansaray", kxy[0], kxy[1], P[i_k, 2] - 0.25, yaw_front_to(-N[i_k, 0] * side, -N[i_k, 1] * side), 1.0, collide=True, cull=0.0)

# ----------------------------------------------------- Bag bolgesi
bag = np.isin(np.array(zone), [R.BAG])
bag_idx = np.where(bag)[0]
row_dir = np.array([math.cos(0.6), math.sin(0.6)])
perp = np.array([-row_dir[1], row_dir[0]])
count = 0
for a in np.arange(-1300, 200, 8.3):
    for b in np.arange(-200, 1500, 3.1):
        x, y = row_dir * a + perp * b
        if x < -1260 or x > -280 or y < 300 or y > 1350:
            continue
        dd = d1(x, y)
        if dd < 9.5 or dd > 130:
            continue
        m = (math.sin(x * 0.03) * math.cos(y * 0.024) + 1) * 0.5
        if m < 0.32 or sample(rock, np.array([x]), np.array([y]))[0] > 0.3:
            continue
        add("BagSira", x, y, h1(x, y) - 0.02, math.degrees(0.6), 1.0, cull=650.0)
        count += 1
print("bag sira", count)
for idx in bag_idx[::8]:
    if rng.random() < 0.72:
        side = rng.choice([-1, 1])
        x, y = P[idx, :2] + N[idx] * side * (HALF[idx] + 3.8)
        add("TasDuvar", x, y, h1(x, y) - 0.08, math.degrees(math.atan2(T[idx, 1], T[idx, 0])), 1.0, collide=True, cull=800.0)
for idx in np.where(np.isin(ZI, [R.BAG, R.KERVAN]))[0][::rng.integers(6, 8)]:
    if rng.random() < 0.55:
        side = rng.choice([-1, 1])
        off = HALF[idx] + rng.uniform(6.0, 13)
        x, y = P[idx, :2] + N[idx] * side * off
        if d1(x, y) > HALF[idx] + 4:
            add(f"Kavak{rng.integers(0, 2)}", x, y, h1(x, y) - 0.1, rng.uniform(0, 360), rng.uniform(0.82, 1.2), collide=True, cull=2400.0)

for _ in range(900):
    x = rng.uniform(-1300, 100)
    y = rng.uniform(-450, 1450)
    dd = d1(x, y)
    if dd < 10 or dd > 280:
        continue
    if sample(lake, np.array([x]), np.array([y]))[0] > 0.1 or h1(x, y) < WATER + 2 or sample(rock, np.array([x]), np.array([y]))[0] > 0.4:
        continue
    add(f"Kayisi{rng.integers(0, 2)}", x, y, h1(x, y) - 0.1, rng.uniform(0, 360), rng.uniform(0.75, 1.3), collide=True, cull=1500.0)

# Nehir kiyisi kavaklari
for x in np.arange(120, 1450, 15.0):
    y = 1010 + 34 * math.sin((x - 535) / 170.0) + 14 * math.sin((x - 535) / 57.0)
    if x < 420:
        continue
    for side in (-1, 1):
        if rng.random() < 0.65:
            yy = y + side * rng.uniform(26, 44)
            if d1(x, yy) > 10:
                add(f"Kavak{rng.integers(0, 2)}", x + rng.uniform(-4, 4), yy, h1(x, yy) - 0.1, rng.uniform(0, 360), rng.uniform(0.85, 1.25), collide=True, cull=2400.0)

# ----------------------------------------------------- Yol kenari otlar ve kayalar
cc = 0
for _ in range(95000):
    i = rng.integers(0, len(P))
    side = rng.choice([-1, 1])
    off = HALF[i] + 1.8 + rng.exponential(10)
    x, y = P[i, :2] + N[i] * side * off + T[i, :2] * rng.uniform(-1, 1)
    if d1(x, y) < HALF[i] + 1.2 or h1(x, y) < WATER + 1.5:
        continue
    if ZI[i] == R.CARSI and off < HALF[i] + 22:
        continue
    r_ = sample(rock, np.array([x]), np.array([y]))[0]
    if r_ > 0.55 and rng.random() < 0.8:
        continue
    add(f"Cali{rng.integers(0, 3)}", x, y, h1(x, y) - 0.04, rng.uniform(0, 360), rng.uniform(0.3, 0.75), cull=170.0)
    cc += 1
print("cali", cc)
for _ in range(2400):
    i = rng.integers(0, len(P))
    side = rng.choice([-1, 1])
    off = HALF[i] + 3.5 + rng.exponential(14)
    x, y = P[i, :2] + N[i] * side * off
    if d1(x, y) < HALF[i] + 2.5 or h1(x, y) < WATER + 1:
        continue
    add(f"Kaya{rng.integers(0, 3)}", x, y, h1(x, y) - 0.1, rng.uniform(0, 360), rng.uniform(0.35, 1.7) * (1.0 + 0.8 * (ZI[i] in (R.VADI, R.TIRMANIS))), collide=False, cull=500.0)

# ----------------------------------------------------- Balonlar: gun dogumu imzasi
for k in range(34):
    a = rng.uniform(0, 2 * math.pi)
    rr = rng.uniform(250, 2600)
    x, y = 100 + math.cos(a) * rr, 700 + math.sin(a) * rr
    add(f"Balon{rng.integers(0, 5)}", x, y, rng.uniform(70, 460), rng.uniform(0, 360), rng.uniform(0.85, 1.2), cull=0.0)

# ----------------------------------------------------- Taranmis CC0 modeller (Tools/bl_scan.py)
_scan_path = os.path.join(ROOT, "RawAssets", "scan.json")
SCAN = json.load(open(_scan_path)) if os.path.exists(_scan_path) else {}
rng2 = np.random.default_rng(1071)  # eski yerlesimleri kaydirmamak icin ayri tohum


def scan_scale(slug, target_max):
    """Birkac model sira halinde taranmis: olcek en uzun kenara gore."""
    return target_max / max(max(SCAN[slug]["size"]), 0.01)


def remap(prefix, slugs, keep, size_range, cull, collide=False):
    """Eski prosedurel varligi taranmis modelle degistirir; keep: tutulacak oran."""
    slugs = [s for s in slugs if s in SCAN]
    if not slugs:
        return
    for key in [k for k in out if k.startswith(prefix)]:
        t = out.pop(key)["t"]
        for i in range(0, len(t), 5):
            if rng2.random() > keep:
                continue
            slug = slugs[rng2.integers(0, len(slugs))]
            add("S_" + slug, t[i], t[i + 1], t[i + 2], rng2.uniform(0, 360), scan_scale(slug, rng2.uniform(*size_range)), collide=collide, cull=cull)


# Alfa maskeli Nanite pahali (olcum: 10 ms). Az ve yakin.
remap("Cali", ["shrub_03", "shrub_04", "wild_rooibos_bush"], 0.07, (0.7, 2.0), 75.0)
remap("Kaya", ["namaqualand_boulder_02", "namaqualand_boulder_03", "namaqualand_boulder_04", "namaqualand_boulder_05", "rock_07", "rock_09"], 0.8, (0.7, 3.6), 500.0)


def clutter(zone_names, slugs, every_m, near, far, cull, scale=(0.92, 1.08), target=None):
    """Yol kenarina esya: gercek boyutunda (scale) ya da en uzun kenar hedefiyle (target)."""
    slugs = [s for s in slugs if s in SCAN]
    if not slugs:
        return
    idx = np.nonzero(np.isin(ZI, zone_names))[0]
    for i in idx[::max(1, int(every_m / R.STEP))]:
        side = rng2.choice([-1, 1])
        off = HALF[i] + rng2.uniform(near, far)
        x, y = P[i, :2] + N[i] * side * off + T[i, :2] * rng2.uniform(-1.5, 1.5)
        if d1(x, y) < HALF[i] + 0.8:
            continue
        slug = slugs[rng2.integers(0, len(slugs))]
        sc = scan_scale(slug, rng2.uniform(*target)) if target else rng2.uniform(*scale)
        add("S_" + slug, x, y, h1(x, y) - 0.01, rng2.uniform(0, 360), sc, cull=cull)


# Carsi: dukkan onu esyasi (yol kenari bariyerinin arkasi)
clutter([R.CARSI], ["wine_barrel_01"], 24, 2.5, 5.0, 220.0)
clutter([R.CARSI], ["wooden_crate_01"], 20, 2.2, 5.0, 180.0)
clutter([R.CARSI], ["wicker_basket_01", "brass_pot_01", "brass_pot_02", "ceramic_pot", "jug_01"], 9, 2.0, 4.5, 110.0)
clutter([R.CARSI], ["planter_pot_clay", "planter_box_01"], 28, 2.0, 4.5, 160.0)
clutter([R.CARSI], ["painted_wooden_chair_01"], 13, 2.5, 5.5, 150.0)
clutter([R.CARSI], ["street_lamp_01"], 42, 1.0, 1.4, 500.0, scale=(1.2, 1.3))
# Kale ve bag yolu: dogal doku
clutter([R.VADI, R.TIRMANIS, R.BAG], ["dead_tree_trunk"], 80, 4.0, 14.0, 500.0, target=(3.0, 6.0))
clutter([R.VADI, R.TIRMANIS, R.BAG, R.KERVAN], ["dry_branches_medium_01"], 34, 1.5, 8.0, 120.0)
clutter([R.VADI, R.KOPRU, R.KALE, R.TIRMANIS], ["namaqualand_stones_01"], 26, 0.8, 4.0, 150.0, target=(1.0, 1.8))
clutter([R.VADI, R.KALE, R.TIRMANIS], ["namaqualand_rocks_01"], 40, 1.5, 6.0, 200.0, target=(1.5, 2.6))

# Seyirci: MetaHuman pisirmeleri (Tools/ue_crowd.py). Yoksa kapsul figurler kalir.
if os.path.exists(os.path.join(ROOT, "RawAssets", "kmsh", "C_Crowd0.kmsh")):
    n_crowd = len([f for f in os.listdir(os.path.join(ROOT, "RawAssets", "kmsh")) if f.startswith("C_Crowd")])
    # Tezgah, cay masasi, esya ve ev icine gomulmesin
    block = []
    for key, rad in (("Tezgah", 2.6), ("CayMasa", 1.5), ("S_wine_barrel", 1.0), ("S_wooden_crate", 1.0), ("S_planter", 0.9), ("S_painted", 0.8), ("Cesme", 3.0)):
        for k in out:
            if k.startswith(key):
                tt = out[k]["t"]
                block += [(tt[i], tt[i + 1], rad) for i in range(0, len(tt), 5)]
    block = np.array(block) if block else np.zeros((0, 3))
    removed = 0
    for key in [k for k in out if k.startswith("Seyirci")]:
        t = out.pop(key)["t"]
        for i in range(0, len(t), 5):
            if len(block) and np.any(np.hypot(block[:, 0] - t[i], block[:, 1] - t[i + 1]) < block[:, 2]):
                removed += 1
                continue
            add(f"C_Crowd{rng2.integers(0, n_crowd)}", t[i], t[i + 1], t[i + 2], t[i + 3], rng2.uniform(0.96, 1.05), cull=300.0)
    print("seyirci cikarilan", removed)

with open(os.path.join(ROOT, "Content", "Kapadokya", "Data", "placements.json"), "w") as f:
    json.dump({"meshes": out}, f)
for k in sorted(out):
    print(f"  {k:12s} {len(out[k]['t']) // 5}")
print("toplam tur", len(out), "ornek", sum(len(v["t"]) // 5 for v in out.values()))
