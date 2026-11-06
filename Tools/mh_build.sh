#!/bin/bash
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
KMH=${1:-Lorenzo} KMOD=ue_mh_build perl -e 'alarm shift; exec @ARGV' ${2:-1500} $E/Engine/Binaries/Mac/UnrealEditor-Cmd $P/KapadokyaTuru.uproject -run=pythonscript -script=$P/Tools/_boot.py -AllowCommandletRendering -unattended -nopause -nosplash -stdout -log > $P/Saved/py_mhb.log 2>&1
echo "MH CIKIS $?"
pkill -f "CrashReport-UE-KapadokyaTuru" || true
grep -aE "MHB|Traceback|LogPython: Error|LogMetaHumanCharacterEditor: Error" $P/Saved/py_mhb.log | cut -c30-170 | tail -40
du -sh $P/Content/Kapadokya/MH
