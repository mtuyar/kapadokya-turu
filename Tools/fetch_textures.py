"""Poly Haven'dan CC0 PBR dokulari indirir (RawAssets/download/tex/<rol>_{diff,nor,arm}.jpg).

Unreal icin DirectX normal haritasi (nor_dx) ve ARM (AO/Roughness/Metallic) kullanilir.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RawAssets", "download", "tex")
UA = {"User-Agent": "KapadokyaTuru-asset-fetch"}

TEX = {
    "asphalt": ("asphalt_02", "2k"),
    "asphaltworn": ("road_damaged", "2k"),
    "cobble": ("cobblestone_floor_01", "2k"),
    "tuff": ("rock_wall_08", "2k"),
    "tuffb": ("sandstone_cracks", "2k"),
    "dryground": ("dry_ground_rocks", "2k"),
    "grass": ("withered_grass", "2k"),
    "dirt": ("stony_dirt_path", "2k"),
    "stone": ("sandstone_blocks_08", "2k"),
    "stonewall": ("rustic_stone_wall", "2k"),
    "plaster": ("clay_plaster", "2k"),
    "plaster2": ("plaster_grey_04", "2k"),
    "roof": ("clay_roof_tiles", "2k"),
    "wood": ("medieval_wood", "2k"),
}


def get_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r, open(dest + ".part", "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(dest + ".part", dest)


def main():
    os.makedirs(OUT, exist_ok=True)
    for role, (asset, res) in TEX.items():
        files = get_json(f"https://api.polyhaven.com/files/{asset}")
        for key, suffix in (("Diffuse", "diff"), ("nor_dx", "nor"), ("arm", "arm")):
            entry = files.get(key)
            if not entry:
                print("EKSIK", asset, key, list(files)[:12], file=sys.stderr)
                continue
            download(entry[res]["jpg"]["url"], os.path.join(OUT, f"{role}_{suffix}.jpg"))
        print("tamam", role, asset, flush=True)


if __name__ == "__main__":
    main()
