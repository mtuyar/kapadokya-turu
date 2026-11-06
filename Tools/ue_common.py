"""Unreal editor Python betikleri icin ortak yardimcilar."""
import os

import unreal

ROOT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()).rstrip("/")
TEX_DIR = os.path.join(ROOT, "RawAssets", "download", "tex")
KMSH_DIR = os.path.join(ROOT, "RawAssets", "kmsh")
GAME = "/Game/Kapadokya"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def import_texture(role, suffix):
    dest = f"{GAME}/Tex"
    name = f"T_{role}_{suffix}"
    path = f"{dest}/{name}"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    task = unreal.AssetImportTask()
    task.filename = os.path.join(TEX_DIR, f"{role}_{suffix}.jpg")
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = True
    TOOLS.import_asset_tasks([task])
    tex = unreal.load_asset(path)
    if suffix == "nor":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif suffix == "arm":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_asset(path)
    return tex


class G:
    """Materyal grafigi kurmak icin kisa yazim."""

    def __init__(self, name, folder="Mat", blend=None, two_sided=False, shading=None):
        self.path = f"{GAME}/{folder}/{name}"
        # Referansli materyali silmek komut satirinda motoru dusuruyor: icini bosaltip yeniden kur
        if EAL.does_asset_exist(self.path):
            self.m = unreal.load_asset(self.path)
            MEL.delete_all_material_expressions(self.m)
        else:
            self.m = TOOLS.create_asset(name, f"{GAME}/{folder}", unreal.Material, unreal.MaterialFactoryNew())
        if blend:
            self.m.set_editor_property("blend_mode", blend)
        if two_sided:
            self.m.set_editor_property("two_sided", True)
        if shading:
            self.m.set_editor_property("shading_model", shading)
        for flag in ("used_with_nanite", "used_with_instanced_static_meshes", "used_with_skeletal_mesh"):
            self.m.set_editor_property(flag, True)
        self.x = -2400

    def node(self, cls, **props):
        self.x += 30
        n = MEL.create_material_expression(self.m, cls, self.x, (self.x * 7) % 1600)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

    def color(self, r, g, b):
        return self.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r, g, b, 1))

    def link(self, a, b, pin="", out=""):
        MEL.connect_material_expressions(a, out, b, pin)

    def op(self, cls, a, b):
        n = self.node(cls)
        for inp, pin in ((a, "A"), (b, "B")):
            if isinstance(inp, (int, float)):
                n.set_editor_property("const_" + pin.lower(), float(inp))
            else:
                self.link(inp, n, pin)
        return n

    def mul(self, a, b):
        return self.op(unreal.MaterialExpressionMultiply, a, b)

    def add(self, a, b):
        return self.op(unreal.MaterialExpressionAdd, a, b)

    def lerp(self, a, b, alpha):
        n = self.node(unreal.MaterialExpressionLinearInterpolate)
        a = self.const(a) if isinstance(a, (int, float)) else a
        b = self.const(b) if isinstance(b, (int, float)) else b
        alpha = self.const(alpha) if isinstance(alpha, (int, float)) else alpha
        self.link(a, n, "A")
        self.link(b, n, "B")
        self.link(alpha, n, "Alpha")
        return n

    def mask(self, a, r=False, g=False, b=False, al=False):
        n = self.node(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=al)
        self.link(a, n)
        return n

    def alpha(self, vc):
        """Kose renginin alfa pini."""
        n = self.node(unreal.MaterialExpressionMultiply, const_b=1.0)
        self.link(vc, n, "A", out="A")
        return n

    def tex(self, texture, uv=None, sampler=None):
        n = self.node(unreal.MaterialExpressionTextureSample, texture=texture)
        if sampler:
            n.set_editor_property("sampler_type", sampler)
        if uv is not None:
            self.link(uv, n, "UVs")
        return n

    def pbr(self, role, uv=None):
        d = self.tex(import_texture(role, "diff"), uv)
        nn = self.tex(import_texture(role, "nor"), uv, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        a = self.tex(import_texture(role, "arm"), uv, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        return d, nn, a

    def custom(self, code, inputs, out=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
        n = self.node(unreal.MaterialExpressionCustom, code=code, output_type=out)
        arr = []
        for name, _ in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", name)
            arr.append(ci)
        n.set_editor_property("inputs", arr)
        for name, src in inputs:
            self.link(src, n, name)
        return n

    def param(self, name, v):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v))

    def vparam(self, name, r, g, b):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=unreal.LinearColor(r, g, b, 1))

    def out(self, node, prop, pin=""):
        MEL.connect_material_property(node, pin, getattr(unreal.MaterialProperty, "MP_" + prop))

    def finish(self):
        MEL.recompile_material(self.m)
        EAL.save_asset(self.path)
        return self.path


def instance(name, parent, scalars=None, vectors=None, textures=None, folder="Mat"):
    path = f"{GAME}/{folder}/{name}"
    if EAL.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = TOOLS.create_asset(name, f"{GAME}/{folder}", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", unreal.load_asset(parent))
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v, 1))
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, v)
    EAL.save_asset(path)
    return path
