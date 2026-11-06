"""Arazi/yol/su aglarini varlik olarak kurar ve bos haritayi olusturur."""
import glob
import json
import os
import sys

import unreal

from ue_common import GAME, KMSH_DIR, ROOT, EAL

lib = unreal.KapadokyaBuildLib
M = f"{GAME}/Mat"
ok = 0
names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(KMSH_DIR, "T_*.kmsh")))
with unreal.ScopedSlowTask(len(names), "arazi") as task:
    for n in names:
        task.enter_progress_frame(1)
        ok += lib.build_mesh_from_file(os.path.join(KMSH_DIR, n + ".kmsh"), f"{GAME}/Gen/Terrain/{n}", [f"{M}/M_Terrain"], True, 1, False)
unreal.log(f"arazi parcasi: {ok}/{len(names)}")
lib.build_mesh_from_file(os.path.join(KMSH_DIR, "Road.kmsh"), f"{GAME}/Gen/Road", [f"{M}/M_RoadAsphalt", f"{M}/M_RoadCobble", f"{M}/M_RoadWorn"], True, 1, False)
lib.build_mesh_from_file(os.path.join(KMSH_DIR, "Horizon.kmsh"), f"{GAME}/Gen/Horizon", [f"{M}/M_Horizon"], True, 0, False)
lib.build_mesh_from_file(os.path.join(KMSH_DIR, "Water.kmsh"), f"{GAME}/Gen/Water", [f"{M}/M_Water"], False, 0, False)

json.dump({"terrain": names}, open(os.path.join(ROOT, "Content/Kapadokya/Data/chunks.json"), "w"))

MAP = f"{GAME}/Maps/L_Kapadokya"
if not EAL.does_asset_exist(MAP):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.new_level(MAP)
    les.save_current_level()
unreal.log("DUNYA AKTARIMI TAMAM")
