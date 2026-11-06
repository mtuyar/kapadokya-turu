"""Editor penceresinde calisir: hazir karakteri kopyalar, editorunu acar, rig ister (Epic girisi burada sorulur)."""
import unreal
PRESET = "/MetaHumanCharacter/Optional/Presets/Lorenzo"
DEST = "/Game/Kapadokya/MH/MH_Lorenzo"
EAL = unreal.EditorAssetLibrary
if not EAL.does_asset_exist(DEST):
    r = EAL.duplicate_asset(PRESET, DEST)
    unreal.log(f"MHL kopya {r}")
ch = unreal.load_asset(DEST)
unreal.log(f"MHL karakter {ch}")
EAL.save_asset(DEST)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([ch])
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
p = unreal.MetaHumanCharacterAutoRiggingRequestParams()
p.blocking = False; p.report_progress = True; p.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
sub.request_auto_rigging(ch, p)
unreal.log("MHL rig istegi gonderildi")
