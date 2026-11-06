#!/bin/bash
# Tum varlik hattini bastan kurar. Kullanim: Tools/build_all.sh
set -e
P=/Volumes/Unreal/Projeler/KapadokyaTuru; cd $P/Tools
B=/Applications/Blender.app/Contents/MacOS/Blender
.venv/bin/python gen_world.py | tail -1
$B -b --factory-startup -P bl_bike.py 2>&1 | grep -E "Traceback|Error:" || true
$B -b --factory-startup -P bl_props.py 2>&1 | grep -E "Traceback|Error:|TAMAM" || true
$B -b --factory-startup -P bl_extras.py 2>&1 | grep -E "Traceback|Error:|File \"|TAMAM" || true
.venv/bin/python gen_audio.py > /dev/null
.venv/bin/python gen_placements.py | tail -45
cd $P
Tools/run_py.sh ue_materials 6
Tools/run_py.sh ue_import_world 6
Tools/run_py.sh ue_import_assets 10
