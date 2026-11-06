import os, unreal
OUT = os.path.join(unreal.Paths.project_saved_dir(), "SkinCheck")
os.makedirs(OUT, exist_ok=True)
for n in ("Lorenzo", "Mateo", "Jorge", "Dominic"):
    ch = unreal.load_asset(f"/Game/Kapadokya/MH/MH_{n}")
    try:
        s = ch.get_editor_property("skin_settings")
        sk = s.get_editor_property("skin")
        unreal.log(f"SKN {n} ton u {sk.u:.3f} v {sk.v:.3f}")
    except Exception as e:
        unreal.log(f"SKN {n} ton okunamadi {e}")
    for t, pth in (("body", f"/Game/Kapadokya/MH/Built/{n}/MH_{n}/Body/Baked/T_Body_BC_VT"), ("head", f"/Game/Kapadokya/MH/Built/{n}/MH_{n}/Face/Baked/T_Head_LOD3_BC_VT")):
        tx = unreal.load_asset(pth)
        if not tx:
            unreal.log(f"SKN {n} {t} yok"); continue
        task = unreal.AssetExportTask(); task.object = tx; task.filename = os.path.join(OUT, f"{n}_{t}.png")
        task.automated = True; task.replace_identical = True; task.prompt = False
        ok = unreal.Exporter.run_asset_export_task(task)
        unreal.log(f"SKN {n} {t} {tx.blueprint_get_size_x()}x{tx.blueprint_get_size_y()} srgb {tx.srgb} {ok}")
unreal.log("SKN TAMAM")
