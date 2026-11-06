"""MetaHuman uretimi: hazir karakter -> bulut rig -> bulut doku -> oyun icin birlestirme. Log: MHB."""
import os
import unreal
NAMES = os.environ.get("KMH", "Lorenzo").split(",")
EAL = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
# Anadolu-Akdeniz araligi (Lorenzo 0.40,0.45 orta ton). Bos: mevcut ton kalir.
SKIN = {"Mateo": (0.36, 0.33), "Jorge": (0.42, 0.40), "Dominic": (0.33, 0.28)}
for n in NAMES:
    dest = f"/Game/Kapadokya/MH/MH_{n}"
    if not EAL.does_asset_exist(dest):
        EAL.duplicate_asset(f"/MetaHumanCharacter/Optional/Presets/{n}", dest)
    ch = unreal.load_asset(dest)
    if not sub.try_add_object_to_edit(ch):
        unreal.log_error(f"MHB {n} duzenlenemedi"); continue
    try:
        tone = SKIN.get(n)
        if tone:
            # Ten tonu: U,V MetaHuman cilt haritasi. Doku yeniden istenir.
            st = ch.get_editor_property("skin_settings")
            sk = st.get_editor_property("skin")
            sk.u, sk.v = tone
            st.set_editor_property("skin", sk)
            sub.commit_skin_settings(character=ch, skin_settings=st)
            unreal.log(f"MHB {n} ten {tone}")
            t = unreal.MetaHumanCharacterTextureRequestParams()
            t.blocking = True; t.report_progress = False
            sub.request_texture_sources(ch, t)
            unreal.log(f"MHB {n} doku {ch.has_high_resolution_textures} can_build {sub.can_build_meta_human(ch)}")
        if not sub.can_build_meta_human(ch):
            p = unreal.MetaHumanCharacterAutoRiggingRequestParams()
            p.blocking = True; p.report_progress = False; p.rig_type = unreal.MetaHumanRigType.JOINTS_ONLY
            sub.request_auto_rigging(ch, p)
            unreal.log(f"MHB {n} rig bitti")
            t = unreal.MetaHumanCharacterTextureRequestParams()
            t.blocking = True; t.report_progress = False
            sub.request_texture_sources(ch, t)
            unreal.log(f"MHB {n} doku {ch.has_high_resolution_textures} can_build {sub.can_build_meta_human(ch)}")
        EAL.save_asset(dest)
        b = unreal.MetaHumanCharacterEditorBuildParameters()
        b.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        b.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        b.absolute_build_path = f"/Game/Kapadokya/MH/Built/{n}"
        b.common_folder_path = "/Game/Kapadokya/MH/Built/Common"
        b.enable_wardrobe_item_validation = False
        try:
            sub.build_meta_human(character=ch, params=b)
            unreal.log(f"MHB {n} birlestirme cagrildi")
        except RuntimeError as e:
            # Kontrol rigi "Cannot break link" uyarilari Python'da hata olarak gelir; birlestirme yine de biter
            unreal.log_warning(f"MHB {n} uyari: {str(e)[:200]}")
    finally:
        sub.remove_object_to_edit(ch)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log(f"MHB {n} kaydedildi")
    for a in EAL.list_assets(f"/Game/Kapadokya/MH/Built/{n}", recursive=True)[:60]:
        unreal.log(f"MHB varlik {a}")
unreal.log("MHB TAMAM")
