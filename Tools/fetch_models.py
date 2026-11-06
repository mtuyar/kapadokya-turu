"""Poly Haven'dan CC0 taranmis modelleri indirir: RawAssets/download/models/<ad>/ (glTF + dokular)."""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RawAssets", "download", "models")
UA = {"User-Agent": "KapadokyaTuru-asset-fetch"}
# ad: cozunurluk
MODELS = {
    "namaqualand_boulder_02": "2k", "namaqualand_boulder_03": "2k", "namaqualand_boulder_04": "2k",
    "namaqualand_boulder_05": "2k", "namaqualand_rocks_01": "2k", "namaqualand_stones_01": "2k",
    "rock_07": "2k", "rock_09": "2k",
    "shrub_03": "1k", "shrub_04": "1k", "shrub_sorrel_01": "1k", "weed_plant_02": "1k", "wild_rooibos_bush": "1k",
    "dry_branches_medium_01": "1k", "dead_tree_trunk": "2k",
    "wooden_barrels_01": "1k", "wine_barrel_01": "1k", "wooden_crate_01": "1k", "wicker_basket_01": "1k",
    "brass_pot_01": "1k", "brass_pot_02": "1k", "ceramic_pot": "1k", "planter_pot_clay": "1k", "jug_01": "1k",
    "painted_wooden_chair_01": "1k", "painted_wooden_table": "1k", "planter_box_01": "1k", "street_lamp_01": "1k",
}


def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(dest + ".part", "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    os.replace(dest + ".part", dest)


for slug, res in MODELS.items():
    try:
        files = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{slug}", headers=UA), timeout=60))
        g = files["gltf"].get(res) or files["gltf"]["1k"]
        g = g["gltf"]
        d = os.path.join(OUT, slug)
        get(g["url"], os.path.join(d, slug + ".gltf"))
        for rel, inc in g.get("include", {}).items():
            safe = os.path.normpath(rel)
            if safe.startswith(".."):
                raise ValueError(rel)
            get(inc["url"], os.path.join(d, safe))
        print("TAMAM", slug, flush=True)
    except Exception as e:
        print("HATA", slug, e, flush=True)
print("INDIRME BITTI", flush=True)
