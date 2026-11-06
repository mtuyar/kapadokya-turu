import unreal
EAL = unreal.EditorAssetLibrary
B = "/Game/Kapadokya/MH/Built/Lorenzo/MH_Lorenzo"
for path in (f"{B}/Body/SKM_MH_Lorenzo_BodyMesh", f"{B}/Face/SKM_MH_Lorenzo_FaceMesh", "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"):
    m = unreal.load_asset(path)
    sk = m.skeleton
    unreal.log(f"MHI == {m.get_name()} iskelet {sk.get_path_name()}")
    for i, s in enumerate(m.materials):
        mi = s.material_interface
        unreal.log(f"MHI slot {i} {s.material_slot_name} {mi.get_path_name() if mi else None}")
vt = unreal.load_asset(f"{B}/Body/Materials/MI_Body_Baked_VT")
unreal.log(f"MHI bodymat ana {vt.parent.get_path_name()}")
for p in vt.texture_parameter_values:
    unreal.log(f"MHI tex {p.parameter_info.name} {p.parameter_value.get_path_name() if p.parameter_value else None} vt={p.parameter_value.virtual_texture_streaming if p.parameter_value else ''}")
unreal.log(f"MHI r.VirtualTextures {unreal.SystemLibrary.get_console_variable_int_value('r.VirtualTextures')}")
sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem) if hasattr(unreal,"SkeletalMeshEditorSubsystem") else None
for path in (f"{B}/Body/SKM_MH_Lorenzo_BodyMesh", f"{B}/Face/SKM_MH_Lorenzo_FaceMesh"):
    m = unreal.load_asset(path)
    if sub:
        n = sub.get_lod_count(m)
        unreal.log(f"MHI {m.get_name()} lod {n} kose {[sub.get_num_verts(m,i) for i in range(n)]}")
unreal.log("MHI TAMAM")
