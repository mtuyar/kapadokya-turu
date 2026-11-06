import os, unreal
from ue_common import GAME, KMSH_DIR
M = f"{GAME}/Mat"
ok = unreal.KapadokyaBuildLib.build_mesh_from_file(os.path.join(KMSH_DIR, "Helmet.kmsh"), f"{GAME}/Gen/Helmet", [f"{M}/MI_Helmet", f"{M}/MI_Dark"], False, 0, False)
unreal.log(f"KASK TAMAM {ok}")
