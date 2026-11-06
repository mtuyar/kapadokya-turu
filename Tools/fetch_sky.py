"""Poly Haven'dan CC0 gokyuzu HDRI indirir ve gunesin konumunu bulur (RawAssets/download/sky)."""
import json, os, urllib.request
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RawAssets", "download", "sky")
UA = {"User-Agent": "KapadokyaTuru-asset-fetch"}
SKIES = {"morning": "qwantani_morning_puresky", "noon": "kloofendal_48d_partly_cloudy_puresky", "sunset": "qwantani_sunset_puresky"}


def read_hdr(path):
    """Radiance RGBE (RLE) okuyucu."""
    data = open(path, "rb").read()
    head, _, rest = data.partition(b"\n\n")
    line, _, body = rest.partition(b"\n")
    p = line.split()
    H, W = int(p[1]), int(p[3])
    img = np.zeros((H, W, 4), np.uint8)
    i = 0
    for y in range(H):
        i += 4
        for c in range(4):
            x = 0
            while x < W:
                n = body[i]; i += 1
                if n > 128:
                    img[y, x:x + n - 128, c] = body[i]; i += 1; x += n - 128
                else:
                    img[y, x:x + n, c] = np.frombuffer(body[i:i + n], np.uint8); i += n; x += n
    e = np.ldexp(1.0, img[..., 3].astype(int) - 136)
    return img[..., :3] * e[..., None]


os.makedirs(OUT, exist_ok=True)
info = {}
for role, slug in SKIES.items():
    dest = os.path.join(OUT, f"sky_{role}.hdr")
    if not os.path.exists(dest):
        files = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{slug}", headers=UA), timeout=40))
        with urllib.request.urlopen(urllib.request.Request(files["hdri"]["4k"]["hdr"]["url"], headers=UA), timeout=300) as r, open(dest, "wb") as f:
            f.write(r.read())
    im = read_hdr(dest)
    lum = im.sum(axis=2) / 3
    H, W = lum.shape
    y, x = np.unravel_index(np.argmax(np.where(lum > 0, lum, 0)), lum.shape)
    top = lum > np.percentile(lum, 99.97)
    ys, xs = np.nonzero(top)
    ang = xs / W * 2 * np.pi
    u = np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi) % 1
    info[role] = dict(slug=slug, sun_u=float(u), sun_elev=float(90 - ys.mean() / H * 180), peak=float(lum.max()),
                      median_sky=float(np.median(lum[:H // 2])), median_low=float(np.median(lum[H // 2 - 200:H // 2])))
    print(role, info[role], os.path.getsize(dest) >> 20, "MB")
json.dump(info, open(os.path.join(OUT, "sky.json"), "w"), indent=1)


def write_hdr(path, im):
    """Radiance RGBE yazici (duz RLE). Gunes kirpilmis gorunum icin."""
    m = im.max(axis=2)
    ex = np.zeros(m.shape, int)
    mant, ex = np.frexp(np.maximum(m, 1e-30))
    sc = np.where(m > 1e-30, mant * 256.0 / np.maximum(m, 1e-30), 0)
    rgbe = np.zeros(im.shape[:2] + (4,), np.uint8)
    rgbe[..., :3] = np.clip(im * sc[..., None], 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(m > 1e-30, ex + 128, 0)
    H, W = m.shape
    with open(path, "wb") as f:
        f.write(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n" % (H, W))
        head = bytes([2, 2, W >> 8, W & 255])
        for y in range(H):
            row = bytearray(head)
            for c in range(4):
                chan = rgbe[y, :, c].tobytes()
                for x in range(0, W, 128):
                    part = chan[x:x + 128]
                    row.append(len(part)); row += part
            f.write(row)


# Gunes diski Sun isigiyla ayrica veriliyor: gokyuzu isigina ikinci kez girmesin
for role in SKIES:
    im = read_hdr(os.path.join(OUT, f"sky_{role}.hdr"))
    lum = im.max(axis=2, keepdims=True)
    limit = 12.0
    write_hdr(os.path.join(OUT, f"skyc_{role}.hdr"), im * np.minimum(1.0, limit / np.maximum(lum, 1e-6)))
print("kirpma tamam")
