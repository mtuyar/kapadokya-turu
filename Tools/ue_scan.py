"""Taranmis modellerin dokulari, materyalleri ve Nanite meshleri."""
import json, os, re
import unreal
from ue_common import G, GAME, ROOT, TOOLS, EAL, KMSH_DIR, instance

M = f"{GAME}/Mat"
SRC = os.path.join(ROOT, "RawAssets", "download", "models")
info = json.load(open(os.path.join(ROOT, "RawAssets", "scan.json")))


def master(name, masked):
    g = G(name, two_sided=masked)
    if masked:
        g.m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    d = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="D", texture=unreal.load_asset("/Engine/EngineResources/DefaultTexture"))
    n = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="N", sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, texture=unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"))
    a = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="A", sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, texture=unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture"))
    tint = g.vparam("Tint", 1, 1, 1)
    g.out(g.mul(d, tint), "BASE_COLOR")
    g.out(n, "NORMAL")
    g.out(g.mask(a, g=True), "ROUGHNESS")
    g.out(g.mask(a, b=True), "METALLIC")
    g.out(g.mask(a, r=True), "AMBIENT_OCCLUSION")
    if masked:
        MEL = unreal.MaterialEditingLibrary
        MEL.connect_material_property(d, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    g.finish()
    return g.path


OP = master("M_Scan", False)
MA = master("M_ScanMasked", True)


def tex(slug, rel, kind):
    if not rel:
        return None
    base = re.sub(r"[^A-Za-z0-9_]", "_", os.path.splitext(os.path.basename(rel))[0])
    name = f"T_{base}"; path = f"{GAME}/Scan/{name}"
    if not EAL.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = os.path.join(SRC, slug, rel)
        task.destination_path = f"{GAME}/Scan"; task.destination_name = name
        task.automated = True; task.save = False; task.replace_existing = True
        TOOLS.import_asset_tasks([task])
        t = unreal.load_asset(path)
        if kind == "n":
            t.set_editor_property("srgb", False)
            t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            t.set_editor_property("flip_green_channel", True)  # glTF normali -> DirectX
        elif kind == "a":
            t.set_editor_property("srgb", False)
            t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        EAL.save_asset(path)
    return unreal.load_asset(path)


lib = unreal.KapadokyaBuildLib
fails = []
for slug, e in sorted(info.items()):
    mats = []
    for i, m in enumerate(e["mats"]):
        textures = {k.upper(): tex(slug, m.get(k), k) for k in ("d", "n", "a")}
        textures = {k: v for k, v in textures.items() if v}
        parent = MA if m.get("alpha") == "MASK" else OP
        mats.append(instance(f"MI_S_{slug}_{i}", parent, None, None, textures))
    src = os.path.join(KMSH_DIR, f"S_{slug}.kmsh")
    coll = 2 if e["size"][2] > 1.2 else 0
    if not lib.build_mesh_from_file(src, f"{GAME}/Gen/S_{slug}", mats, True, coll, False):
        fails.append(slug)
unreal.log(f"SCAN aktarim {len(info) - len(fails)}/{len(info)} EKSIK={fails}")
unreal.log("SCAN TAMAM")
