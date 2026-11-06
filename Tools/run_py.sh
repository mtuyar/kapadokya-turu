#!/bin/bash
# Kullanim: Tools/run_py.sh modul_adi  -> editor komut satirinda Tools/modul_adi.py calistirir
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
LOG=$P/Saved/py_$1.log; mkdir -p $P/Saved
KMOD=$1 $E/Engine/Binaries/Mac/UnrealEditor-Cmd $P/KapadokyaTuru.uproject -run=pythonscript -script=$P/Tools/_boot.py -unattended -nopause -nosplash -NullRHI -stdout -log > $LOG 2>&1
echo "exit $?"; grep -E "LogPython: (Error|Warning)|Traceback|LogPython.*TAMAM|LogPython: [a-z]|Error: " $LOG | grep -vE "Condition failed|init_unreal" | cut -c1-220 | tail -${2:-25}
