"""Kapadokya Turu parkuru: kontrol noktalarindan kapali rota uretir.

Birimler metre. X/Y/Z dogrudan Unreal eksenleridir (Z yukari, sol el).
Kontrol noktasi: (x, y, z, bolge). Bolge o noktadan sonraki yolu tanimlar.
"""
import numpy as np

CARSI, VADI, KOPRU, TIRMANIS, KALE, BAG, KERVAN = "carsi", "vadi", "kopru", "tirmanis", "kale", "bag", "kervan"

# Yuzey: 0 asfalt, 1 arnavut kaldirimi, 2 yipranmis asfalt
ZONE_SURFACE = {CARSI: 1, VADI: 0, KOPRU: 1, TIRMANIS: 2, KALE: 1, BAG: 0, KERVAN: 2}
ZONE_HALFWIDTH = {CARSI: 4.5, VADI: 3.6, KOPRU: 3.0, TIRMANIS: 3.2, KALE: 3.4, BAG: 3.6, KERVAN: 3.6}
ZONE_TITLE = {
    CARSI: "Peri Köyü Çarşısı", VADI: "Peribacası Vadisi", KOPRU: "Kızılırmak Köprüsü",
    TIRMANIS: "Kale Tırmanışı", KALE: "Kale Zirvesi", BAG: "Bağ Yolu", KERVAN: "Kervansaray Düzlüğü",
}

CONTROL = [
    (-260, -120, 20, CARSI), (-60, -125, 20, CARSI), (120, -120, 20, CARSI), (290, -105, 19, CARSI),
    (430, -35, 15, VADI), (535, 95, 8, VADI), (560, 255, -2, VADI), (670, 395, -14, VADI),
    (850, 445, -24, VADI), (985, 565, -32, VADI), (965, 745, -38, VADI), (800, 835, -42, VADI),
    (625, 885, -44, KOPRU), (540, 1010, -44, KOPRU), (525, 1150, -44, KOPRU),
    (575, 1262, -40, TIRMANIS), (740, 1300, -27, TIRMANIS), (885, 1318, -15, TIRMANIS),
    (952, 1372, -7, TIRMANIS), (890, 1428, 2, TIRMANIS), (720, 1432, 16, TIRMANIS), (560, 1432, 30, TIRMANIS),
    (478, 1486, 38, TIRMANIS), (550, 1542, 47, TIRMANIS), (700, 1552, 58, TIRMANIS), (802, 1592, 66, TIRMANIS),
    (792, 1662, 73, TIRMANIS), (660, 1682, 81, TIRMANIS), (480, 1680, 90, TIRMANIS), (300, 1640, 98, TIRMANIS),
    (160, 1520, 102, KALE), (70, 1380, 103, KALE), (-60, 1245, 100, KALE),
    (-240, 1160, 92, BAG), (-420, 1190, 76, BAG), (-610, 1140, 62, BAG), (-760, 1000, 50, BAG),
    (-830, 810, 42, BAG), (-790, 620, 36, BAG), (-860, 440, 31, BAG),
    (-930, 250, 28, KERVAN), (-900, 60, 25, KERVAN), (-760, -70, 23, KERVAN), (-560, -125, 21, KERVAN),
]

STEP = 2.0


def catmull(p0, p1, p2, p3, t):
    # Merkezcil olmayan klasik form; kontrol noktalari yeterince esit aralikli
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def build():
    ctrl = np.array([c[:3] for c in CONTROL], float)
    zones_ctrl = [c[3] for c in CONTROL]
    n = len(ctrl)
    pts, zidx = [], []
    for i in range(n):
        for t in np.linspace(0, 1, 120, endpoint=False):
            pts.append(catmull(ctrl[(i - 1) % n], ctrl[i], ctrl[(i + 1) % n], ctrl[(i + 2) % n], t))
            zidx.append(i)
    pts = np.array(pts)
    closed = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(closed[:, :2], axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    count = int(round(L / STEP))
    si = np.linspace(0, L, count, endpoint=False)
    out = np.stack([np.interp(si, s, closed[:, k]) for k in range(3)], axis=1)
    # Z'yi yumusat: bisiklet yolunda ani egim degisimi olmasin
    z = out[:, 2]
    for _ in range(3):
        k = 41
        z = np.convolve(np.r_[z[-k:], z, z[:k]], np.ones(k) / k, mode="same")[k:-k]
    out[:, 2] = z
    idx = np.searchsorted(s, si, side="right") - 1
    zone = [zones_ctrl[zidx[min(i, len(zidx) - 1)]] for i in idx]
    return out, zone, si, L


def metrics(p):
    n = len(p)
    d = np.roll(p[:, :2], -1, axis=0) - np.roll(p[:, :2], 1, axis=0)
    t = d / np.linalg.norm(d, axis=1, keepdims=True)
    heading = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    # 10 m penceresinde egrilik
    w = 5
    dh = (np.roll(heading, -w) - np.roll(heading, w))
    dh = (dh + np.pi) % (2 * np.pi) - np.pi
    kappa = dh / (2 * w * STEP)
    w2 = 10
    grade = (np.roll(p[:, 2], -w2) - np.roll(p[:, 2], w2)) / (2 * w2 * STEP)
    return t, kappa, grade


if __name__ == "__main__":
    import os
    import sys
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.spatial import cKDTree

    p, zone, s, L = build()
    t, kappa, grade = metrics(p)
    print(f"uzunluk {L:.0f} m, nokta {len(p)}")
    print(f"z {p[:,2].min():.1f}..{p[:,2].max():.1f}; egim {grade.min()*100:.1f}%..{grade.max()*100:.1f}%")
    r = 1 / np.maximum(np.abs(kappa), 1e-4)
    print(f"en dar viraj yaricapi {r.min():.1f} m")
    tree = cKDTree(p[:, :2])
    pairs = tree.query_pairs(30.0, output_type="ndarray")
    gap = np.abs(pairs[:, 0] - pairs[:, 1])
    gap = np.minimum(gap, len(p) - gap)
    bad = pairs[gap > 60]
    print("birbirine 30 m'den yakin farkli yol kollari:", len(bad), (p[bad[:5, 0], :2].round() if len(bad) else ""))
    zs = sorted(set(zone), key=zone.index)
    for z in zs:
        m = np.array([a == z for a in zone])
        print(f"  {z:9s} {m.sum()*STEP:6.0f} m  egim ort {grade[m].mean()*100:5.1f}%  maks {grade[m].max()*100:5.1f}%")
    fig, ax = plt.subplots(1, 2, figsize=(14, 6))
    colors = {CARSI: "k", VADI: "tab:orange", KOPRU: "tab:blue", TIRMANIS: "tab:red", KALE: "tab:purple", BAG: "tab:green", KERVAN: "tab:brown"}
    for z in zs:
        m = np.array([a == z for a in zone])
        ax[0].scatter(p[m, 0], p[m, 1], s=1, c=colors[z], label=z)
    ax[0].axis("equal")
    ax[0].legend()
    ax[1].plot(s, p[:, 2])
    ax[1].set_title("Yukselti")
    fig.savefig(sys.argv[1] if len(sys.argv) > 1 else "route.png", dpi=80)
