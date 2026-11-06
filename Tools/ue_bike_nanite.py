"""Bisiklet ve kask Nanite: 12 bisikletin Nanite'siz golge ve taban gecisi pahaliydi."""
import os, unreal
from ue_common import GAME, KMSH_DIR
M = f"{GAME}/Mat"
BIKE = [f"{M}/MI_BikePaint", f"{M}/MI_BikeCarbon", f"{M}/MI_BikeMetal", f"{M}/MI_Rubber"]
lib = unreal.KapadokyaBuildLib
for n in ("BikeFrame", "BikeSteer", "BikeWheel", "BikeCrank", "BikePedal"):
    ok = lib.build_mesh_from_file(os.path.join(KMSH_DIR, n + ".kmsh"), f"{GAME}/Gen/{n}", BIKE, True, 0, False)
    unreal.log(f"BN {n} {ok}")
lib.build_mesh_from_file(os.path.join(KMSH_DIR, "Helmet.kmsh"), f"{GAME}/Gen/Helmet", [f"{M}/MI_Helmet", f"{M}/MI_Dark"], True, 0, False)
unreal.log("BN TAMAM")
