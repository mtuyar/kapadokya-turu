"""MetaHuman seyirci: her kisi icin pozlu statik mesh pisirir. Forma rengi ornek basina (PerInstanceCustomData)."""
import os
import unreal
from ue_common import G, GAME, KMSH_DIR, instance
lib = unreal.KapadokyaBuildLib
M = f"{GAME}/Mat"
PEOPLE = os.environ.get("KMH", "Lorenzo,Mateo,Jorge,Dominic").split(",")
ST = unreal.MaterialSamplerType

g = G("M_CrowdSkin")
wp = g.node(unreal.MaterialExpressionVertexColor)
bc = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BC", sampler_type=ST.SAMPLERTYPE_VIRTUAL_COLOR, texture=unreal.load_asset(f"{GAME}/MH/Built/Lorenzo/MH_Lorenzo/Body/Baked/T_Body_BC_VT"))
nr = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="N", sampler_type=ST.SAMPLERTYPE_VIRTUAL_NORMAL, texture=unreal.load_asset(f"{GAME}/MH/Built/Lorenzo/MH_Lorenzo/Body/Baked/T_Body_N_VT"))
lp = g.node(unreal.MaterialExpressionVertexInterpolator)
g.link(g.node(unreal.MaterialExpressionPreSkinnedPosition), lp, "VS")
col = g.custom("""
if (P.z < 11.0) return Dark;
return C;
""", [("P", lp), ("C", bc), ("Dark", g.vparam("Shoe", 0.03, 0.025, 0.02))])
g.out(col, "BASE_COLOR"); g.out(nr, "NORMAL"); g.out(g.const(0.55), "ROUGHNESS")
g.finish()

g = G("M_CrowdShirt", two_sided=True)
a = g.node(unreal.MaterialExpressionPerInstanceCustomData, data_index=0)
b = g.node(unreal.MaterialExpressionPerInstanceCustomData, data_index=1)
c = g.node(unreal.MaterialExpressionPerInstanceCustomData, data_index=2)
ab = g.node(unreal.MaterialExpressionAppendVector); g.link(a, ab, "A"); g.link(b, ab, "B")
abc = g.node(unreal.MaterialExpressionAppendVector); g.link(ab, abc, "A"); g.link(c, abc, "B")
g.out(abc, "BASE_COLOR"); g.out(g.const(0.75), "ROUGHNESS")
g.finish()
short = instance("MI_CrowdShort", f"{M}/M_Color", {"Rough": 0.8}, {"Color": (0.03, 0.035, 0.05)})

HAIR = [(0.018, 0.012, 0.009), (0.03, 0.018, 0.011), (0.012, 0.01, 0.009), (0.06, 0.035, 0.018)]
idx = 0
for name in PEOPLE:
    base = f"{GAME}/MH/Built/{name}/MH_{name}"
    if not unreal.EditorAssetLibrary.does_asset_exist(f"{base}/Body/SKM_MH_{name}_BodyMesh"):
        unreal.log_warning(f"CROWD {name} yok"); continue
    skin = instance(f"MI_CrowdSkin_{name}", f"{M}/M_CrowdSkin", None, None, {"BC": unreal.load_asset(f"{base}/Body/Baked/T_Body_BC_VT"), "N": unreal.load_asset(f"{base}/Body/Baked/T_Body_N_VT")})
    # Yuz: motorun yuz materyali statik mesh'te siyah cikiyor; kendi cilt materyalimiz ve kafanin dokulari
    head = instance(f"MI_CrowdHead_{name}", f"{M}/M_CrowdSkin", None, None, {"BC": unreal.load_asset(f"{base}/Face/Baked/T_Head_LOD3_BC_VT"), "N": unreal.load_asset(f"{base}/Face/Baked/T_Head_LOD3_N_VT")})
    mats = [skin, f"{M}/M_CrowdShirt", short, head, f"{base}/Face/Materials/MI_Teeth_Baked", f"{base}/Face/Materials/MI_EyeL_Baked", f"{base}/Face/Materials/MI_EyeR_Baked"]
    hair_path, hair_mi = "", None
    for asset in unreal.EditorAssetLibrary.list_assets(f"{base}/Grooms", recursive=False):
        short_name = asset.split("/")[-1].split(".")[0]
        if short_name.startswith("Hair_") and short_name.endswith("CardsMesh_Group0_LOD3"):
            hair_path = asset
        if short_name.startswith("MI_WI_Hair_") and short_name.endswith("_Hair"):
            hair_mi = asset.split(".")[0]
    unreal.log(f"CROWD {name} sac {hair_path} {hair_mi}")
    # Grom materyali sac verisi ister (statikte gri cikar): duz koyu renk
    tone = HAIR[idx // 2 % len(HAIR)]
    mats.append(instance(f"MI_CrowdHair_{name}", f"{M}/M_Color", {"Rough": 0.65}, {"Color": tone}))
    for pose in (idx % 4, (idx + 1) % 4):
        out = os.path.join(KMSH_DIR, f"C_Crowd{idx}.kmsh")
        ok = lib.bake_human_pose(f"{base}/Body/SKM_MH_{name}_BodyMesh", f"{base}/Clothing/MH_{name}_Outfits", f"{base}/Face/SKM_MH_{name}_FaceMesh", hair_path, 1, pose, out)
        built = ok and lib.build_mesh_from_file(out, f"{GAME}/Gen/C_Crowd{idx}", mats, True, 0, False)
        unreal.log(f"CROWD {idx} {name} poz {pose} pisirme {ok} mesh {built}")
        idx += 1
unreal.log(f"CROWD TAMAM {idx}")
