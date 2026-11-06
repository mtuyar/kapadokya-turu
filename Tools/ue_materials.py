"""Ana materyalleri kurar."""
import unreal

from ue_common import G, GAME, instance, import_texture

CUSTOM_ROCK_UV = """
float3 n = abs(N);
float2 uv = WP.xy;
if (n.z < 0.62) uv = n.x > n.y ? float2(WP.y, WP.z) : float2(WP.x, WP.z);
return uv * Scale;
"""

CUSTOM_STRATA = """
// Tuf katmanlari: yukseklige gore krem-pembe-oksit bantlari (Kizilcukur/Gorem renkleri)
float z = WP.z / 100.0 + Wobble * 6.0;
float a = sin(z * 0.55) * 0.5 + 0.5;
float b = sin(z * 1.9 + 1.3) * 0.5 + 0.5;
float c = sin(z * 0.13 + 0.4) * 0.5 + 0.5;
float3 cream = float3(0.95, 0.87, 0.74);
float3 pink = float3(0.90, 0.72, 0.63);
float3 ochre = float3(0.85, 0.72, 0.53);
float3 col = lerp(cream, pink, smoothstep(0.35, 0.9, a) * c);
col = lerp(col, ochre, smoothstep(0.6, 1.0, b) * 0.55);
return col * 1.1;
"""

CUSTOM_ROAD_LINES = """
// U: enine 0-1 (0.5 orta), V: boyuna (metre/4)
float meters = UV.y * 4.0;
float lat = abs(UV.x - 0.5) * 2.0;
float edge = smoothstep(0.885, 0.895, lat) * (1.0 - smoothstep(0.915, 0.925, lat));
float dash = step(frac(meters / 9.0), 0.42);
float centre = (1.0 - smoothstep(0.012, 0.018, abs(UV.x - 0.5))) * dash;
float wear = saturate(Noise * 1.8 - 0.35);
return saturate(edge * Enable + centre * Enable) * (0.35 + 0.65 * wear);
"""

CUSTOM_WATER_NORMAL = """
float t = Time * 0.6;
float2 p = WP.xy / 100.0;
float2 g = 0;
g += float2(0.8, 0.3) * cos(dot(p, float2(0.8, 0.3)) * 0.9 + t * 1.3) * 0.5;
g += float2(-0.4, 0.9) * cos(dot(p, float2(-0.4, 0.9)) * 2.1 + t * 1.9) * 0.28;
g += float2(0.6, -0.7) * cos(dot(p, float2(0.6, -0.7)) * 4.6 + t * 2.7) * 0.16;
g += float2(0.2, 1.0) * cos(dot(p, float2(0.2, 1.0)) * 9.3 + t * 3.8) * 0.08;
return normalize(float3(-g * Amp, 1.0));
"""


def world_uv(g, scale):
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    uv = g.mask(wp, r=True, g=True)
    return g.mul(uv, scale / 100.0)


def terrain():
    g = G("M_Terrain")
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    vn = g.node(unreal.MaterialExpressionVertexNormalWS)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    scale = g.const(1.0 / 1500.0)
    rock_uv = g.custom(CUSTOM_ROCK_UV, [("WP", wp), ("N", vn), ("Scale", scale)], unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    rock_uv2 = g.mul(rock_uv, 0.21)
    rd, rn, ra = g.pbr("tuff", rock_uv)
    rd2 = g.tex(import_texture("tuffb", "diff"), rock_uv2)
    wobble = g.mask(rd2, r=True)
    strata = g.custom(CUSTOM_STRATA, [("WP", wp), ("Wobble", wobble)])
    macro = g.mul(rd2, 1.6)
    rock_col = g.mul(g.mul(g.mul(g.mask(rd, r=True), 1.5), strata), g.mul(g.mask(rd2, g=True), 1.9))
    uv_g = world_uv(g, 1.0 / 5.0)
    gd, gn, ga = g.pbr("grass", uv_g)
    uv_d = world_uv(g, 1.0 / 6.0)
    dd, dn, da = g.pbr("dryground", uv_d)
    grass_tint = g.mul(gd, g.color(0.92, 0.88, 0.62))
    ground = g.lerp(g.mul(dd, g.color(1.05, 0.93, 0.78)), grass_tint, g.mask(vc, g=True))
    gnor = g.lerp(dn, gn, g.mask(vc, g=True))
    garm = g.lerp(da, ga, g.mask(vc, g=True))
    rock_a = g.mask(vc, r=True)
    col = g.lerp(ground, rock_col, rock_a)
    nor = g.lerp(gnor, rn, rock_a)
    arm = g.lerp(garm, ra, rock_a)
    # Yol kenari ve koy duzlugu: toprak
    sd, sn, sa = g.pbr("dirt", world_uv(g, 1.0 / 4.0))
    b = g.mask(vc, b=True)
    col = g.lerp(col, g.mul(sd, g.color(0.98, 0.88, 0.72)), b)
    nor = g.lerp(nor, sn, b)
    arm = g.lerp(arm, sa, b)
    # Islak kiyi
    shore = g.alpha(vc)
    col = g.lerp(col, g.mul(col, 0.45), shore)
    g.out(col, "BASE_COLOR")
    g.out(nor, "NORMAL")
    g.out(g.mask(arm, r=True), "AMBIENT_OCCLUSION")
    g.out(g.mask(arm, g=True), "ROUGHNESS")
    g.finish()


def horizon():
    g = G("M_Horizon")
    vc = g.node(unreal.MaterialExpressionVertexColor)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    uv = g.mul(g.mask(wp, r=True, g=True), 1.0 / 90000.0)
    d = g.tex(import_texture("tuffb", "diff"), uv)
    earth = g.mul(g.lerp(g.color(0.34, 0.30, 0.21), g.color(0.45, 0.37, 0.30), g.mask(vc, r=True)), g.mul(d, 2.0))
    col = g.lerp(earth, g.color(0.92, 0.94, 0.98), g.mask(vc, b=True))
    g.out(col, "BASE_COLOR")
    g.out(g.const(0.9), "ROUGHNESS")
    g.finish()


def road(name, role, lines, tile, tint=(1, 1, 1)):
    g = G(name)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    uv = g.mul(g.mask(wp, r=True, g=True), 1.0 / (tile * 100.0))
    d, n, a = g.pbr(role, uv)
    macro = g.tex(import_texture("dryground", "diff"), g.mul(uv, 0.043))
    noise = g.mask(macro, g=True)
    col = g.mul(g.mul(d, g.color(*tint)), g.add(0.55, g.mul(noise, 1.2)))
    paint = g.custom(CUSTOM_ROAD_LINES, [("UV", tc), ("Noise", noise), ("Enable", g.const(1.0 if lines else 0.0))], unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    col = g.lerp(col, g.color(0.78, 0.76, 0.68), paint)
    # Kenar: banket toprakla karisir
    dd = g.tex(import_texture("dirt", "diff"), uv)
    lat = g.mask(g.node(unreal.MaterialExpressionVertexColor), g=True)
    edge = g.node(unreal.MaterialExpressionSmoothStep, const_min=0.93, const_max=1.0)
    g.link(lat, edge, "Value")
    col = g.lerp(col, dd, edge)
    g.out(col, "BASE_COLOR")
    g.out(n, "NORMAL")
    g.out(g.mask(a, r=True), "AMBIENT_OCCLUSION")
    g.out(g.lerp(g.mask(a, g=True), 0.5, paint), "ROUGHNESS")
    g.finish()


def water():
    g = G("M_Water")
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    t = g.node(unreal.MaterialExpressionTime)
    nrm = g.custom(CUSTOM_WATER_NORMAL, [("WP", wp), ("Time", t), ("Amp", g.const(0.11))])
    fres = g.node(unreal.MaterialExpressionFresnel, exponent=4.0, base_reflect_fraction=0.04)
    # Kizilirmak: demirli, kirmizi-kahverengi ton
    g.out(g.lerp(g.color(0.055, 0.035, 0.022), g.color(0.11, 0.075, 0.05), fres), "BASE_COLOR")
    g.out(g.const(0.04), "ROUGHNESS")
    g.out(g.const(0.6), "SPECULAR")
    g.out(nrm, "NORMAL")
    g.finish()


def color_master():
    """Duz renk + puruz + metal; bisiklet ve aksesuarlar."""
    g = G("M_Color")
    vc = g.node(unreal.MaterialExpressionVertexColor)
    g.out(g.mul(g.vparam("Color", 0.5, 0.5, 0.5), vc), "BASE_COLOR")
    g.out(g.param("Rough", 0.5), "ROUGHNESS")
    g.out(g.param("Metal", 0.0), "METALLIC")
    g.finish()


def pbr_master():
    """Mimari: dunya olcekli UV (UV0 metre), kosede tint ve eskime."""
    g = G("M_Pbr")
    tc = g.node(unreal.MaterialExpressionTextureCoordinate, coordinate_index=0)
    uv = g.mul(tc, g.param("Tile", 0.33))
    d = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="D", texture=import_texture("stone", "diff"))
    n = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="N", texture=import_texture("stone", "nor"), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    a = g.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="A", texture=import_texture("stone", "arm"), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    for s in (d, n, a):
        g.link(uv, s, "UVs")
    vc = g.node(unreal.MaterialExpressionVertexColor)
    g.out(g.mul(g.mul(d, g.vparam("Tint", 1, 1, 1)), vc), "BASE_COLOR")
    g.out(n, "NORMAL")
    g.out(g.mask(a, r=True), "AMBIENT_OCCLUSION")
    g.out(g.mask(a, g=True), "ROUGHNESS")
    path = g.finish()
    for name, role, tile, tint in (
        ("MI_Stone", "stone", 0.33, (1.45, 1.32, 1.12)),
        ("MI_StoneWall", "stonewall", 0.4, (1.4, 1.28, 1.08)),
        ("MI_Plaster", "plaster2", 0.3, (1.5, 1.44, 1.3)),
        ("MI_Roof", "roof", 0.5, (1.0, 0.82, 0.68)),
        ("MI_Wood", "wood", 0.5, (0.78, 0.62, 0.48)),
        ("MI_Tuff", "tuff", 0.16, (1.0, 0.82, 0.68)),
    ):
        instance(name, path, {"Tile": tile}, {"Tint": tint},
                 {"D": import_texture(role, "diff"), "N": import_texture(role, "nor"), "A": import_texture(role, "arm")})


if __name__ == "__main__" or __import__("os").environ.get("KMOD") == "ue_materials":
    terrain()
    horizon()
    road("M_RoadAsphalt", "asphalt", True, 3.0, (1.05, 1.03, 1.0))
    road("M_RoadCobble", "cobble", False, 2.6, (1.0, 0.92, 0.82))
    road("M_RoadWorn", "asphaltworn", True, 3.5, (1.0, 0.98, 0.95))
    water()
    color_master()
    pbr_master()
    unreal.log("MATERYALLER TAMAM")
