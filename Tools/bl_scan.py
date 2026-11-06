"""Taranmis CC0 modelleri KMSH'e cevirir. RawAssets/kmsh/S_<ad>.kmsh ve RawAssets/scan.json yazar.
Calistirma: Blender -b --factory-startup -P Tools/bl_scan.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import addon_utils
import bpy
import bl_common as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "RawAssets", "download", "models")
# Nanite oldugu icin ucgen siniri comert; bellek ve aktarim suresi icin ust sinir var
LIMIT = {"default": 120000}
info = {}
for slug in sorted(os.listdir(SRC)):
    d = os.path.join(SRC, slug)
    g = os.path.join(d, slug + ".gltf")
    if not os.path.exists(g):
        continue
    C.clear_scene()
    addon_utils.enable("io_scene_gltf2")
    bpy.ops.import_scene.gltf(filepath=g)
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if not objs:
        print("BOS", slug); continue
    bpy.ops.object.select_all(action="DESELECT")
    tris = 0
    for o in objs:
        o.select_set(True)
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    lim = LIMIT["default"]
    if tris > lim:
        m = o.modifiers.new("dec", "DECIMATE")
        m.ratio = lim / tris
    xs = [(o.matrix_world @ v.co) for v in o.data.vertices]
    minx, maxx = min(v.x for v in xs), max(v.x for v in xs)
    miny, maxy = min(v.y for v in xs), max(v.y for v in xs)
    minz, maxz = min(v.z for v in xs), max(v.z for v in xs)
    org = ((minx + maxx) / 2, (miny + maxy) / 2, minz)
    names = [m.name for m in o.data.materials]
    slots = {n: i for i, n in enumerate(names)}
    C.export_kmsh([o], f"S_{slug}.kmsh", slots, origin=org)
    # Doku esleme: glTF materyal tablosundan
    gj = json.load(open(g))
    imgs = [i.get("uri") for i in gj.get("images", [])]
    tex = [imgs[t["source"]] for t in gj.get("textures", [])]
    mats = {}
    for mt in gj.get("materials", []):
        pb = mt.get("pbrMetallicRoughness", {})
        pick = lambda e: tex[e["index"]] if e else None
        mats[mt["name"]] = dict(d=pick(pb.get("baseColorTexture")), a=pick(pb.get("metallicRoughnessTexture")),
                                n=pick(mt.get("normalTexture")), alpha=mt.get("alphaMode", "OPAQUE"), two=mt.get("doubleSided", False))
    info[slug] = dict(size=[maxx - minx, maxy - miny, maxz - minz], tris=tris, mats=[dict(mats.get(n.split(".")[0], mats.get(n, {})), name=n) for n in names])
    print("SCAN", slug, "boyut", [round(x, 2) for x in info[slug]["size"]], "ucgen", tris, "materyal", names, flush=True)
json.dump(info, open(os.path.join(ROOT, "RawAssets", "scan.json"), "w"), indent=1)
print("SCAN TAMAM", len(info), flush=True)
