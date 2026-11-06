"""MetaHuman sporcu materyalleri: gercek cilt + boyali ayakkabi/corap/eldiven; forma ve sort."""
import unreal
from ue_common import G, GAME, instance
B = f"{GAME}/MH/Built/Lorenzo/MH_Lorenzo/Body/Baked"
C = f"{GAME}/MH/Built/Common/Optional/Clothing/Common/Materials/Crewneckt/Male"
ST = unreal.MaterialSamplerType


def preskin(g):
    vs = g.node(unreal.MaterialExpressionPreSkinnedPosition)
    ps = g.node(unreal.MaterialExpressionVertexInterpolator)
    g.link(vs, ps, "VS")
    return ps


# Cilt (govde). Olcek: ayak bilegi z~9, baldir z~52, el x~48 (A-pozu, cm)
g = G("M_RiderMH")
p = preskin(g)
bc = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BC", sampler_type=ST.SAMPLERTYPE_VIRTUAL_COLOR, texture=unreal.load_asset(f"{B}/T_Body_BC_VT"))
nr = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="N", sampler_type=ST.SAMPLERTYPE_VIRTUAL_NORMAL, texture=unreal.load_asset(f"{B}/T_Body_N_VT"))
sr = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="SRMF", sampler_type=ST.SAMPLERTYPE_VIRTUAL_MASKS, texture=unreal.load_asset(f"{B}/T_Body_SRMF_VT"))
col = g.custom("""
float z = P.z; float ax = abs(P.x);
float3 c = Skin;
if (z < 12.0) c = float3(0.012, 0.012, 0.014);           // ayakkabi
else if (z < 24.0) c = float3(0.82, 0.82, 0.84);         // corap
if (ax > 46.0 && z < 107.0) c = float3(0.015, 0.015, 0.018);          // eldiven
return c;
""", [("P", p), ("Skin", bc)])
rough = g.custom("""
float z = P.z; float ax = abs(P.x);
if (z < 24.0 || (ax > 46.0 && z < 107.0)) return 0.62;
return R;
""", [("P", p), ("R", g.mask(sr, g=True))], unreal.CustomMaterialOutputType.CMOT_FLOAT1)
g.out(col, "BASE_COLOR")
g.out(nr, "NORMAL")
g.out(rough, "ROUGHNESS")
g.finish()

# Forma ve sort: takim rengi, gogus bandi ve kol ucu. Ince kumas dokusu prosedurel.
g = G("M_JerseyCloth", two_sided=True)
p = preskin(g)
col = g.custom("""
float z = P.z; float ax = abs(P.x);
float3 c = Jersey;
if (abs(z - 127.0) < 4.5 && ax < 24.0) c = Jersey2;
if (ax > 26.0 && ax < 29.5) c = Jersey2;
return c;
""", [("P", p), ("Jersey", g.vparam("Jersey", 0.7, 0.03, 0.03)), ("Jersey2", g.vparam("Jersey2", 0.9, 0.9, 0.9))])
g.out(col, "BASE_COLOR")
g.out(g.param("Rough", 0.62), "ROUGHNESS")
g.finish()
unreal.log("RIDERMH TAMAM")
