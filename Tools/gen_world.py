"""Arazi, yol, nehir ve ufuk aglarini + rota verisini uretir.

Cikti:
  RawAssets/kmsh/T_x_y.kmsh    arazi parcalari (3 m cozunurluk)
  RawAssets/kmsh/Horizon.kmsh  uzak arazi (Erciyes dahil)
  RawAssets/kmsh/Road.kmsh     yol seridi
  RawAssets/world.npz          yerlesim betigi icin yukseklik alani
  Content/Kapadokya/Data/route.json
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree

import kmsh
import route as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RawAssets", "kmsh")
DATA = os.path.join(ROOT, "Content", "Kapadokya", "Data")
os.makedirs(OUT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

XMIN, XMAX, YMIN, YMAX = -1500.0, 1500.0, -600.0, 2200.0
CELL = 3.0
WATER_Z = -50.0
LAKE = np.array([60.0, 620.0])
LAKE_R = 430.0
BRIDGE_Y = 1010.0
rng = np.random.default_rng(1071)  # Malazgirt


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fbm(shape, base, octaves, gain=0.5, seed=0):
    """Spektral olmayan, hizli fBm: filtrelenmis beyaz gurultu katmanlari (hucre cinsinden)."""
    g = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, sigma, total = 1.0, base, 0.0
    for _ in range(octaves):
        n = gaussian_filter(g.standard_normal(shape).astype(np.float32), sigma, mode="wrap")
        n /= n.std() + 1e-6
        out += amp * n
        total += amp
        amp *= gain
        sigma = max(sigma * 0.5, 0.6)
    return out / total


def river_y(x):
    return BRIDGE_Y + 34 * np.sin((x - 535) / 170.0) + 14 * np.sin((x - 535) / 57.0)


# ---------------------------------------------------------------- rota
P, zone, S, L = R.build()
T, KAPPA, GRADE = R.metrics(P)
N2 = np.stack([-T[:, 1], T[:, 0]], axis=1)  # yol enine yonu
halfw = np.array([R.ZONE_HALFWIDTH[z] for z in zone])
for _ in range(2):
    k = 25
    halfw = np.convolve(np.r_[halfw[-k:], halfw, halfw[:k]], np.ones(k) / k, "same")[k:-k]
surface = np.array([R.ZONE_SURFACE[z] for z in zone], int)
zones = sorted(set(zone), key=zone.index)
zone_i = np.array([zones.index(z) for z in zone])

# ---------------------------------------------------------------- uzak alan (40 km, 100 m)
HCELL = 100.0
hx = np.arange(-20000, 20001, HCELL)
hy = np.arange(-19000, 21001, HCELL)
HX, HY = np.meshgrid(hx, hy)
hn = fbm(HX.shape, 22, 6, 0.55, seed=11)
hr = fbm(HX.shape, 4, 4, 0.5, seed=12)
dcentre = np.hypot(HX - 0, HY - 800)
H_far = 15 + smooth(1500, 9000, dcentre) * (160 + 190 * hn + 40 * np.abs(hr))
# Erciyes: karli volkan, guneydoguda
ex, ey = 15500.0, -11500.0
de = np.hypot(HX - ex, HY - ey) / 5200.0
ang = np.arctan2(HY - ey, HX - ex)
ridges = 1 + 0.12 * np.sin(ang * 9 + hn * 2) + 0.06 * np.sin(ang * 23)
H_far += 2650 * np.exp(-(de * ridges) ** 1.25)
# Hasan Dagi benzeri ikinci silindir, batida daha alcak
dh = np.hypot(HX + 16000, HY - 6000) / 3800.0
H_far += 1200 * np.exp(-(dh) ** 1.4)


def far_height(x, y):
    return map_coordinates(H_far, [(y - hy[0]) / HCELL, (x - hx[0]) / HCELL], order=1)


# ---------------------------------------------------------------- yakin arazi
xs = np.arange(XMIN, XMAX + 0.01, CELL)
ys = np.arange(YMIN, YMAX + 0.01, CELL)
GX, GY = np.meshgrid(xs, ys)
shape = GX.shape
print("arazi", shape)

tree = cKDTree(P[:, :2])
D, I = tree.query(np.stack([GX.ravel(), GY.ravel()], axis=1), workers=-1)
D = D.reshape(shape).astype(np.float32)
I = I.reshape(shape)
roadz = P[I, 2].astype(np.float32)
zmask = zone_i[I]

# Rota yuksekliginin yumusak alani: yol etrafinda dogal yamac zemini
sub = P[::10]
cx = np.arange(XMIN, XMAX + 1, 40.0)
cy = np.arange(YMIN, YMAX + 1, 40.0)
CX, CY = np.meshgrid(cx, cy)
d2 = (CX[..., None] - sub[:, 0]) ** 2 + (CY[..., None] - sub[:, 1]) ** 2 + 400.0
w = d2 ** -1.6
coarse = (w * sub[:, 2]).sum(-1) / w.sum(-1)
base = map_coordinates(coarse, [(GY - YMIN) / 40.0, (GX - XMIN) / 40.0], order=3).astype(np.float32)

n_large = fbm(shape, 60, 6, 0.5, seed=1)
n_mid = fbm(shape, 14, 5, 0.55, seed=2)
n_fine = fbm(shape, 2.2, 3, 0.6, seed=3)
n_warp = fbm(shape, 40, 3, 0.5, seed=4)
ridged = 1 - np.abs(fbm(shape, 25, 5, 0.5, seed=5)) * 1.6


def zone_weight(names, blur=45):
    m = np.isin(zmask, [zones.index(n) for n in names]).astype(np.float32)
    return gaussian_filter(m, blur / CELL)


w_vadi = zone_weight([R.VADI, R.KOPRU])
w_tir = zone_weight([R.TIRMANIS, R.KALE])
w_bag = zone_weight([R.BAG])
w_town = zone_weight([R.CARSI])
w_kerv = zone_weight([R.KERVAN])

away = smooth(14, 150, D)
H = base + away * (9 * n_large + 3 * n_mid)
# Bag ve kervan bolgesi: yumusak tepeler, tarla
H += (w_bag + w_kerv) * away * (5 * n_large)
# Vadi: tuf kanyonu. Yoldan uzaklastikca basamakli duvarlarla yukselir.
canyon = smooth(38, 150, D) * (34 + 26 * n_large + 16 * ridged)
strata = canyon + n_warp * 3
step = 7.0
terr = np.floor(strata / step) * step + step * smooth(0.55, 1.0, (strata / step) % 1.0)
H += w_vadi * terr
# Tirmanis: daha sert, kayali yamac ve basamakli tuf
H += w_tir * smooth(25, 150, D) * (16 + 18 * ridged + 10 * n_large)
# Koy duzlugu
town_d = np.hypot((GX - 20) / 620.0, (GY + 120) / 300.0)
flat = 1 - smooth(0.7, 1.15, town_d)
H = H * (1 - flat) + (20 + 0.25 * n_mid) * flat

# Kale kayasi: Uchisar benzeri dev kutle, zirve bolgesinin kuzeybatisinda
kd = np.hypot(GX + 70, GY - 1520) / 120.0
H += 70 * np.exp(-(kd ** 2.2)) * (1 + 0.15 * n_mid)

# Sinirda uzak araziye gecis
edge = np.minimum.reduce([GX - XMIN, XMAX - GX, GY - YMIN, YMAX - GY])
blend_far = 1 - smooth(0, 260, edge)
H = H * (1 - blend_far) + far_height(GX, GY) * blend_far

# Baraj golu (cevrimin ic bolgesi) ve Kizilirmak
ld = np.hypot(GX - LAKE[0], GY - LAKE[1]) + 40 * n_large
lake_w = 1 - smooth(LAKE_R * 0.72, LAKE_R * 1.08, ld)
H = H * (1 - lake_w) + (WATER_Z - 5 + 2 * n_mid) * lake_w
# Nehir: dogudan gelir, kopruden gecer, gole dokulur
ry = river_y(GX)
in_channel = GX > LAKE[0]
rd = np.abs(GY - ry)
# Kopruden sonra gole dogru egilen kisim
bend = smooth(420, 150, GX)
target_y = ry * (1 - bend) + (LAKE[1] + 200) * bend
rd = np.abs(GY - target_y)
river_w = (1 - smooth(16, 42, rd + 6 * n_mid)) * in_channel
H = H * (1 - river_w) + (WATER_Z - 3.5) * river_w

# Asgari kot: su duzeyinin altina yanlislikla inme (gol ve nehir disinda)
keep = (lake_w < 0.05) & (river_w < 0.05)
H = np.where(keep, np.maximum(H, WATER_Z + 1.5 + np.maximum(0, n_large)), H)

# Mikro detay
H += n_fine * (0.10 + 0.5 * away * (1 - flat))

# Yol koridoru: yolun altina gomulur, kenarlarda yumusak gecis
corridor_w = halfw[I] + 2.2
roadfit = 1 - smooth(corridor_w, corridor_w + 30.0, D)
# Kopru ayaginda nehir oyugu korunur
on_bridge = (np.abs(GY - river_y(GX)) < 38) & (np.abs(GX - 535) < 45)
roadfit = np.where(on_bridge, 0.0, roadfit)
H = H * (1 - roadfit) + (roadz - 0.30) * roadfit

# ---------------------------------------------------------------- renk maskeleri
gy, gx = np.gradient(H, CELL)
slope = np.hypot(gx, gy)
nrm = np.stack([-gx, -gy, np.ones_like(H)], axis=-1)
nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)

rock = smooth(0.42, 0.85, slope + 0.10 * n_mid)
rock = np.maximum(rock, w_vadi * smooth(0.25, 0.55, slope))
grass = (1 - rock) * smooth(-0.5, 0.8, n_mid + w_bag * 0.9 + 0.4 * n_fine - w_vadi * 0.8 - flat * 0.3)
grass *= 1 - smooth(0, 6, WATER_Z + 3 - H) * 0  # tutarli
shore = 1 - smooth(WATER_Z + 0.5, WATER_Z + 4, H)
grass = np.maximum(grass, shore * 0.6)
shoulder = 1 - smooth(corridor_w - 1, corridor_w + 7, D)
color = np.stack([rock, grass, np.maximum(shoulder, flat * 0.75), shore], axis=-1)
color = (np.clip(color, 0, 1) * 255).astype(np.uint8)

# ---------------------------------------------------------------- parcalar
CHUNK = 84  # hucre
written = []
ny, nx = shape
for j in range(0, ny - 1, CHUNK):
    for i in range(0, nx - 1, CHUNK):
        j2, i2 = min(j + CHUNK, ny - 1), min(i + CHUNK, nx - 1)
        sy, sx = j2 - j + 1, i2 - i + 1
        idx = np.arange(sy * sx, dtype=np.uint32).reshape(sy, sx)
        a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
        # UE sol el: yukari bakan on yuz icin saat yonu (x->y)
        tris = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([b, c, d], -1).reshape(-1, 3)])
        px = GX[j:j2 + 1, i:i2 + 1].ravel() * 100
        py = GY[j:j2 + 1, i:i2 + 1].ravel() * 100
        pz = H[j:j2 + 1, i:i2 + 1].ravel() * 100
        cen = np.array([px.mean(), py.mean(), pz.mean()], np.float32)
        pos = np.stack([px, py, pz], axis=1)
        uv = np.stack([px / 100.0, py / 100.0], axis=1)
        name = f"T_{i // CHUNK:02d}_{j // CHUNK:02d}"
        kmsh.write(os.path.join(OUT, name + ".kmsh"), pos, nrm[j:j2 + 1, i:i2 + 1].reshape(-1, 3),
                   uv, color[j:j2 + 1, i:i2 + 1].reshape(-1, 4), tris)
        written.append(name)
print("parca", len(written))

# ---------------------------------------------------------------- ufuk
hmask = np.ones_like(H_far)
HZ = H_far.copy()
inside = (HX > XMIN + 120) & (HX < XMAX - 120) & (HY > YMIN + 120) & (HY < YMAX - 120)
HZ[inside] = WATER_Z - 40  # yakin arazinin altina gizle
gy2, gx2 = np.gradient(HZ, HCELL)
n2 = np.stack([-gx2, -gy2, np.ones_like(HZ)], -1)
n2 /= np.linalg.norm(n2, axis=-1, keepdims=True)
sy, sx = HZ.shape
idx = np.arange(sy * sx, dtype=np.uint32).reshape(sy, sx)
a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
tris = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([b, c, d], -1).reshape(-1, 3)])
snow = smooth(1500, 2100, HZ + 180 * hn)
farrock = smooth(0.25, 0.6, np.hypot(gx2, gy2))
col = (np.stack([farrock, 1 - farrock, snow, np.zeros_like(snow)], -1).clip(0, 1) * 255).astype(np.uint8)
kmsh.write(os.path.join(OUT, "Horizon.kmsh"), np.stack([HX.ravel(), HY.ravel(), HZ.ravel()], 1) * 100, n2.reshape(-1, 3),
           np.stack([HX.ravel(), HY.ravel()], 1) / 100.0, col.reshape(-1, 4), tris)

# ---------------------------------------------------------------- yol
offs = np.array([-1.0, -0.82, -0.5, -0.25, 0.0, 0.25, 0.5, 0.82, 1.0])
n = len(P)
m = len(offs) + 4  # iki yanda ikiser banket koseleri
pos, nor, uv, col = [], [], [], []
for i in range(n):
    w_ = halfw[i]
    # Viraj yatisi: dar virajda en fazla %4
    bank = float(np.clip(KAPPA[i] * 2.0, -0.04, 0.04))
    lats = np.concatenate([[-w_ - 1.4, -w_ - 0.5], offs * w_, [w_ + 0.5, w_ + 1.4]])
    for la in lats:
        xy = P[i, :2] + N2[i] * la
        crown = -0.018 * abs(min(abs(la), w_))
        drop = -0.28 * smooth(w_ + 0.1, w_ + 1.4, abs(la))
        z = P[i, 2] + crown + bank * la + drop
        pos.append((xy[0] * 100, xy[1] * 100, z * 100))
        col.append((surface[i] * 80, int(255 * min(abs(la) / max(w_, 0.1), 1.0)), 0, 255))
        uv.append((la / (2 * w_) + 0.5, S[i] / 4.0))
pos = np.array(pos, np.float32)
# Dikis normalleri
V = pos.reshape(n, m, 3)
du = np.roll(V, -1, 0) - np.roll(V, 1, 0)
dv = np.gradient(V, axis=1)
nn = np.cross(du, dv)  # sag el yon: asagida duzelt
nn = nn / np.linalg.norm(nn, axis=-1, keepdims=True)
nn = np.where(nn[..., 2:3] < 0, -nn, nn)
idx = np.arange(n * m, dtype=np.uint32).reshape(n, m)
tr = []
mats = []
for i in range(n):
    i2 = (i + 1) % n
    surf = surface[i]
    for j in range(m - 1):
        a_, b_, c_, d_ = idx[i, j], idx[i, j + 1], idx[i2, j], idx[i2, j + 1]
        # Enine vektor (+sol), boyuna vektor ileri. X-ileri/Y-sol duzeninde UE on yuzu:
        tr.append((a_, b_, c_))
        tr.append((b_, d_, c_))
        mats += [surf, surf]
kmsh.write(os.path.join(OUT, "Road.kmsh"), pos, nn.reshape(-1, 3), np.array(uv, np.float32),
           np.array(col, np.uint8), np.array(tr, np.uint32), np.array(mats, np.uint8))

# ---------------------------------------------------------------- su
wp = np.array([[-22000, -21000, WATER_Z], [22000, -21000, WATER_Z], [-22000, 23000, WATER_Z], [22000, 23000, WATER_Z]], float)
# Goru sadece gol-nehir bolgesi: kucuk plaka
wp = np.array([[XMIN, YMIN, WATER_Z], [XMAX, YMIN, WATER_Z], [XMIN, YMAX, WATER_Z], [XMAX, YMAX, WATER_Z]], float)
kmsh.write(os.path.join(OUT, "Water.kmsh"), wp * 100, np.tile([0, 0, 1], (4, 1)), wp[:, :2] / 10.0,
           np.full((4, 4), 255, np.uint8), np.array([[0, 2, 1], [1, 2, 3]], np.uint32))

# ---------------------------------------------------------------- veriler
np.savez_compressed(os.path.join(ROOT, "RawAssets", "world.npz"), H=H.astype(np.float32), D=D, xs=xs, ys=ys,
                    rock=rock.astype(np.float32), grass=grass.astype(np.float32), lake=lake_w.astype(np.float32),
                    river=river_w.astype(np.float32), I=I.astype(np.int32))

json.dump({
    "length": L,
    "step": R.STEP,
    "zones": zones,
    "titles": [R.ZONE_TITLE[z] for z in zones],
    "x": np.round(P[:, 0] * 100, 1).tolist(),
    "y": np.round(P[:, 1] * 100, 1).tolist(),
    "z": np.round(P[:, 2] * 100, 1).tolist(),
    "halfwidth": np.round(halfw * 100, 1).tolist(),
    "surface": surface.tolist(),
    "zone": zone_i.tolist(),
    "curvature": np.round(KAPPA / 100.0, 7).tolist(),
    "bounds": [XMIN * 100, XMAX * 100, YMIN * 100, YMAX * 100],
    "water_z": WATER_Z * 100,
}, open(os.path.join(DATA, "route.json"), "w"))

print("tepe", H.max(), "dip", H.min(), "su alani %", 100 * (H < WATER_Z).mean())
if len(sys.argv) > 1:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    ls = LightSource(315, 35)
    shaded = ls.hillshade(H[::2, ::2], vert_exag=1.2, dx=CELL * 2, dy=CELL * 2)
    img = np.dstack([shaded * (0.75 + 0.25 * rock[::2, ::2]), shaded * (0.65 + 0.35 * grass[::2, ::2]), shaded * 0.55])
    img[H[::2, ::2] < WATER_Z] = (0.15, 0.3, 0.5)
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.imshow(img, origin="lower", extent=[XMIN, XMAX, YMIN, YMAX])
    ax.plot(P[:, 0], P[:, 1], "r-", lw=0.6)
    fig.savefig(sys.argv[1], dpi=90)
