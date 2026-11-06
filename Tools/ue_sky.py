"""HDRI gokyuzu: kubemap aktarimi ve kubbe materyali."""
import os
import unreal
from ue_common import G, GAME, ROOT, TOOLS, EAL

for role in ("morning", "noon", "sunset"):
    name = f"T_sky_{role}"; path = f"{GAME}/Sky/{name}"
    task = unreal.AssetImportTask()
    task.filename = os.path.join(ROOT, "RawAssets", "download", "sky", f"skyc_{role}.hdr")
    task.destination_path = f"{GAME}/Sky"; task.destination_name = name
    task.automated = True; task.save = False; task.replace_existing = True
    TOOLS.import_asset_tasks([task])
    t = unreal.load_asset(path)
    unreal.log(f"gok {name} {type(t).__name__}")
    EAL.save_asset(path)

g = G("M_SkyDome", two_sided=True, shading=unreal.MaterialShadingModel.MSM_UNLIT)
g.m.set_editor_property("is_sky", True)
cam = g.node(unreal.MaterialExpressionCameraVectorWS)
dirn = g.custom("float a=Yaw*0.017453293; float s=sin(a), c=cos(a); float3 d=-CamV; return float3(d.x*c-d.y*s, d.x*s+d.y*c, d.z);",
                [("CamV", cam), ("Yaw", g.param("Yaw", 0.0))])
tex = g.node(unreal.MaterialExpressionTextureSampleParameterCube, parameter_name="Cube", texture=unreal.load_asset(f"{GAME}/Sky/T_sky_noon"))
g.link(dirn, tex, "UVs")
g.out(g.mul(tex, g.param("Intensity", 1.0)), "EMISSIVE_COLOR")
g.finish()
unreal.log("GOK TAMAM")
