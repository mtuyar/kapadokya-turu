#!/bin/bash
# Editor penceresinde MetaHuman uretimi. Kullanim: Tools/mh_gui.sh Lorenzo,Mateo sure
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
L="$HOME/Library/Logs/Unreal Engine/KapadokyaTuruEditor/KapadokyaTuru.log"
KTOOLS=$P/Tools PYTHONPATH=$P/Tools KMH=${1:-Lorenzo} perl -e 'alarm shift; exec @ARGV' ${2:-1500} $E/Engine/Binaries/Mac/UnrealEditor $P/KapadokyaTuru.uproject "-ExecCmds=py $P/Tools/ue_mh_gui.py" -nosound -log > $P/Saved/mh_gui.log 2>&1
echo "MH CIKIS $?"
pkill -f "CrashReport-UE-KapadokyaTuru" || true
grep -aE "MHB|Traceback|LogMetaHuman[A-Za-z]*: Error|MetaHuman: Error|TG_AsyncExportTask" "$L" | cut -c30-180 | tail -45
du -sh $P/Content/Kapadokya/MH $P/Content/Kapadokya/MH/Built 2>/dev/null
