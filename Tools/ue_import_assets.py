"""Sesler, sporcu ve tum prop materyalleri, prop aglari."""
import glob
import os

import unreal

from ue_common import EAL, G, GAME, KMSH_DIR, ROOT, TOOLS, import_texture, instance
from ue_materials import CUSTOM_ROCK_UV, CUSTOM_STRATA

M = f"{GAME}/Mat"
lib = unreal.KapadokyaBuildLib

# ------------------------------------------------- sesler
AUDIO = os.path.join(ROOT, "RawAssets", "audio")
LOOPING = {"S_Tyre", "S_Wind", "S_Freewheel", "S_Chain", "S_Cobble", "S_Breath", "S_Crowd", "S_Music"}
for wav in sorted(glob.glob(os.path.join(AUDIO, "*.wav"))):
    name = os.path.basename(wav)[:-4]
    path = f"{GAME}/Audio/{name}"
    if not EAL.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.filename = wav
        task.destination_path = f"{GAME}/Audio"
        task.destination_name = name
        task.automated = True
        task.save = False
        task.replace_existing = True
        TOOLS.import_asset_tasks([task])
    s = unreal.load_asset(path)
    s.set_editor_property("looping", name in LOOPING)
    EAL.save_asset(path)
unreal.log("sesler tamam")

# ------------------------------------------------- materyaller
g = G("M_Tuff")
wp = g.node(unreal.MaterialExpressionWorldPosition)
vn = g.node(unreal.MaterialExpressionVertexNormalWS)
uv = g.custom(CUSTOM_ROCK_UV, [("WP", wp), ("N", vn), ("Scale", g.const(1.0 / 1100.0))], unreal.CustomMaterialOutputType.CMOT_FLOAT2)
d, n, a = g.pbr("tuff", uv)
macro = g.tex(import_texture("tuffb", "diff"), g.mul(uv, 0.19))
strata = g.custom(CUSTOM_STRATA, [("WP", wp), ("Wobble", g.mask(macro, r=True))])
g.out(g.mul(g.mul(g.mul(g.mul(g.mask(d, r=True), 2.3), strata), g.mul(g.mask(macro, g=True), 2.5)), g.color(1.0, 0.89, 0.72)), "BASE_COLOR")
g.out(n, "NORMAL")
g.out(g.mask(a, r=True), "AMBIENT_OCCLUSION")
g.out(g.mask(a, g=True), "ROUGHNESS")
g.finish()

g = G("M_Basalt")
wp = g.node(unreal.MaterialExpressionWorldPosition)
vn = g.node(unreal.MaterialExpressionVertexNormalWS)
uv = g.custom(CUSTOM_ROCK_UV, [("WP", wp), ("N", vn), ("Scale", g.const(1.0 / 300.0))], unreal.CustomMaterialOutputType.CMOT_FLOAT2)
d, n, a = g.pbr("tuff", uv)
g.out(g.mul(d, g.color(0.17, 0.145, 0.125)), "BASE_COLOR")
g.out(n, "NORMAL")
g.out(g.mask(a, g=True), "ROUGHNESS")
g.finish()

# Yaprak ve kart: iki yuzlu, kose renkli
g = G("M_Leaf", two_sided=True, shading=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
vc = g.node(unreal.MaterialExpressionVertexColor)
g.out(vc, "BASE_COLOR")
g.out(g.const(0.62), "ROUGHNESS")
g.out(g.mul(vc, g.color(0.45, 0.55, 0.2)), "SUBSURFACE_COLOR")
g.finish()

# Bayrak: rüzgar dalgasi (alfa = direkten uzaklik)
g = G("M_Flag", two_sided=True)
vc = g.node(unreal.MaterialExpressionVertexColor)
tm = g.node(unreal.MaterialExpressionTime)
wp = g.node(unreal.MaterialExpressionWorldPosition)
wave = g.custom("""
float u = U;
float a = sin(u * 9.0 - T * 6.0 + WP.x * 0.002) * 16.0 * u + sin(u * 4.0 - T * 3.3) * 10.0 * u;
return float3(0, a, sin(u * 6.0 - T * 4.5) * 3.0 * u);
""", [("U", g.alpha(vc)), ("T", tm), ("WP", wp)])
g.out(vc, "BASE_COLOR")
g.out(g.const(0.75), "ROUGHNESS")
g.out(wave, "WORLD_POSITION_OFFSET")
g.finish()

# Sporcu: pre-skin konumdan forma, sort, cilt, ayakkabi
g = G("M_Rider")
ps_vs = g.node(unreal.MaterialExpressionPreSkinnedPosition)
ps = g.node(unreal.MaterialExpressionVertexInterpolator)
g.link(ps_vs, ps, "VS")
col = g.custom("""
float3 p = P;
float ax = abs(p.x);
float z = p.z;
float3 c = Skin;
if (z < 13.0) c = float3(0.82, 0.82, 0.84);                 // ayakkabi
else if (z < 26.0) c = float3(0.85, 0.85, 0.86);            // corap
else if (z < 58.0) c = Skin;                                // bacak
else if (z < 108.0 && ax < 30.0) c = float3(0.012, 0.012, 0.016);  // sort
else if (z < 150.0) {
    if (ax < 52.0) {
        c = Jersey;
        float band = abs(z - 126.0);
        if (band < 4.5) c = Jersey2;
        if (ax > 40.0 && ax < 44.0) c = Jersey2;
    } else c = Skin;                                         // on kol ve el
} else if (z < 174.0 && ax < 8.0) c = Skin;
else c = Skin;
if (ax > 72.0) c = float3(0.02, 0.02, 0.02);                  // eldiven
return c;
""", [("P", ps), ("Skin", g.vparam("Skin", 0.6, 0.4, 0.3)), ("Jersey", g.vparam("Jersey", 0.7, 0.03, 0.03)), ("Jersey2", g.vparam("Jersey2", 0.9, 0.9, 0.9))])
g.out(col, "BASE_COLOR")
g.out(g.const(0.55), "ROUGHNESS")
g.finish()

instance("MI_Dark", f"{M}/M_Color", {"Rough": 0.85}, {"Color": (0.06, 0.05, 0.045)})
instance("MI_Lead", f"{M}/M_Color", {"Rough": 0.55, "Metal": 0.9}, {"Color": (0.42, 0.44, 0.47)})
instance("MI_Glass", f"{M}/M_Color", {"Rough": 0.08, "Metal": 1.0}, {"Color": (0.05, 0.07, 0.08)})
instance("MI_Brass", f"{M}/M_Color", {"Rough": 0.3, "Metal": 1.0}, {"Color": (0.85, 0.62, 0.22)})
instance("MI_Vertex", f"{M}/M_Color", {"Rough": 0.7}, {"Color": (1, 1, 1)})
instance("MI_Banner", f"{M}/M_Color", {"Rough": 0.55}, {"Color": (0.62, 0.03, 0.03)})
instance("MI_BikePaint", f"{M}/M_Color", {"Rough": 0.22}, {"Color": (0.72, 0.02, 0.03)})
instance("MI_BikeCarbon", f"{M}/M_Color", {"Rough": 0.3}, {"Color": (0.012, 0.012, 0.014)})
instance("MI_BikeMetal", f"{M}/M_Color", {"Rough": 0.25, "Metal": 1.0}, {"Color": (0.72, 0.72, 0.74)})
instance("MI_Rubber", f"{M}/M_Color", {"Rough": 0.82}, {"Color": (0.018, 0.018, 0.018)})
instance("MI_Helmet", f"{M}/M_Color", {"Rough": 0.25}, {"Color": (0.86, 0.86, 0.88)})
instance("MI_Lens", f"{M}/M_Color", {"Rough": 0.05, "Metal": 1.0}, {"Color": (0.09, 0.03, 0.02)})

ARCH = [f"{M}/MI_Stone", f"{M}/MI_StoneWall", f"{M}/MI_Plaster", f"{M}/MI_Roof", f"{M}/MI_Wood", f"{M}/MI_Dark", f"{M}/MI_Lead", f"{M}/MI_Glass", f"{M}/MI_Banner", f"{M}/MI_Vertex", f"{M}/MI_Brass"]
ROCK = list(ARCH)
ROCK[2] = f"{M}/M_Tuff"
ROCK[5] = f"{M}/M_Basalt"
LEAFY = list(ARCH)
LEAFY[9] = f"{M}/M_Leaf"
FLAG = list(ARCH)
FLAG[9] = f"{M}/M_Flag"
BALLOON = list(ARCH)
BALLOON[8] = f"{M}/MI_Vertex"
STALL = list(ARCH)
STALL[8] = f"{M}/MI_Vertex"
BIKE = [f"{M}/MI_BikePaint", f"{M}/MI_BikeCarbon", f"{M}/MI_BikeMetal", f"{M}/MI_Rubber"]
HEAD = [f"{M}/MI_Helmet", f"{M}/MI_Dark", f"{M}/MI_Lens"]

# ad: (materyaller, collision mod: 0 yok,1 trimesh,2 kutu, nanite)
TABLE = {
    "BikeFrame": (BIKE, 0, True), "BikeSteer": (BIKE, 0, True), "BikeWheel": (BIKE, 0, True), "BikeCrank": (BIKE, 0, True), "BikePedal": (BIKE, 0, True),
    "Helmet": (HEAD, 0, False), "Glasses": (HEAD, 0, False),
    "Cami": (ARCH, 2, True), "Kervansaray": (ARCH, 1, True), "Kopru": (ARCH, 0, True), "Cesme": (ARCH, 2, True),
    "Bayrak": (FLAG, 0, False), "Flama": (ARCH, 0, False), "Kemer": (ARCH, 0, True), "Bariyer": (ARCH, 2, False), "CayMasa": (ARCH, 0, True),
    "KaleKaya": (ROCK, 1, True), "TasDuvar": (ARCH, 2, True), "BagSira": (LEAFY, 0, True),
}
for i in range(5):
    TABLE[f"Chimney{i}"] = (ROCK, 1, True)
    TABLE[f"Balon{i}"] = (BALLOON, 0, True)
for i in range(4):
    TABLE[f"Konak{i}"] = (ARCH, 2, True)
    TABLE[f"Seyirci{i}"] = (STALL, 0, True)
for i in range(3):
    TABLE[f"Magara{i}"] = (ROCK, 1, True)
    TABLE[f"Tezgah{i}"] = (STALL, 0, True)
    TABLE[f"Cali{i}"] = (LEAFY, 0, True)
    TABLE[f"Kaya{i}"] = (ROCK, 0, True)
for i in range(2):
    TABLE[f"Kavak{i}"] = (LEAFY, 2, True)
    TABLE[f"Kayisi{i}"] = (LEAFY, 2, True)
# Tek yaprak materyali: kavak/kayisi govdesi tahta
TABLE["Flama"] = (STALL, 0, False)

fails = []
with unreal.ScopedSlowTask(len(TABLE), "proplar") as task:
    for name, (materials, coll, nanite) in sorted(TABLE.items()):
        task.enter_progress_frame(1)
        src = os.path.join(KMSH_DIR, name + ".kmsh")
        if not os.path.exists(src):
            fails.append(name + " (dosya yok)")
            continue
        if not lib.build_mesh_from_file(src, f"{GAME}/Gen/{name}", materials, nanite, coll, False):
            fails.append(name)
unreal.log(f"prop: {len(TABLE) - len(fails)}/{len(TABLE)} EKSIK={fails}")
unreal.log("VARLIKLAR TAMAM")
