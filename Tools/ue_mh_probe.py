"""MetaHuman sondasi: olustur, buluta rig iste, durumu yaz."""
import unreal
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
path = "/Game/Kapadokya/MH/MH_Probe"
if unreal.EditorAssetLibrary.does_asset_exist(path):
    ch = unreal.load_asset(path)
else:
    ch = tools.create_asset("MH_Probe", "/Game/Kapadokya/MH", unreal.MetaHumanCharacter, unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
unreal.log(f"MHP karakter {ch}")
ok = sub.try_add_object_to_edit(character=ch)
unreal.log(f"MHP duzenleme {ok}")
p = unreal.MetaHumanCharacterAutoRiggingRequestParams()
p.blocking = True; p.report_progress = False; p.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
sub.request_auto_rigging(character=ch, params=p)
unreal.log(f"MHP rig sonrasi can_build {sub.can_build_meta_human(character=ch, log_error=True) if False else sub.can_build_meta_human(ch)}")
t = unreal.MetaHumanCharacterTextureRequestParams()
t.blocking = True; t.report_progress = False
sub.request_texture_sources(character=ch, params=t)
unreal.log(f"MHP doku {ch.has_high_resolution_textures} can_build {sub.can_build_meta_human(ch)}")
unreal.EditorAssetLibrary.save_asset(path)
unreal.log("MHP TAMAM")
