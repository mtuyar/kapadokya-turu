"""Sadece peribacasi materyalini yeniden kurar (tum varliklari yeniden aktarmadan)."""
import unreal
from ue_common import G, import_texture
from ue_materials import CUSTOM_ROCK_UV, CUSTOM_STRATA
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
unreal.log("TUF TAMAM")
