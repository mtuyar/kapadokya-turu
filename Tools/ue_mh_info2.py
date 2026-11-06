import unreal
B = "/Game/Kapadokya/MH/Built/Lorenzo/MH_Lorenzo"
m = unreal.load_asset(f"{B}/Clothing/MH_Lorenzo_Outfits")
unreal.log(f"MHI2 iskelet {m.skeleton.get_path_name()}")
for i, s in enumerate(m.materials):
    mi = s.material_interface
    unreal.log(f"MHI2 slot {i} {s.material_slot_name} {mi.get_path_name() if mi else None} ana {mi.parent.get_path_name() if mi and hasattr(mi,'parent') and mi.parent else None}")
    if mi and hasattr(mi, "texture_parameter_values"):
        for p in mi.texture_parameter_values:
            unreal.log(f"MHI2   tex {p.parameter_info.name} {p.parameter_value.get_path_name() if p.parameter_value else None}")
        for p in mi.vector_parameter_values:
            unreal.log(f"MHI2   vec {p.parameter_info.name} {p.parameter_value}")
        for p in mi.scalar_parameter_values[:14]:
            unreal.log(f"MHI2   sca {p.parameter_info.name} {p.parameter_value}")
unreal.log("MHI2 TAMAM")
