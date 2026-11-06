#!/bin/bash
# Kullanim: Tools/perf.sh ad kalite "cvar1=deger,cvar2=deger"
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
N=$1; Q=$2; X=$3; LOG=$P/Saved/perf_$N.log
perl -e "alarm shift; exec @ARGV" 200 $E/Engine/Binaries/Mac/UnrealEditor $P/KapadokyaTuru.uproject -game -windowed -ResX=1600 -ResY=900 -KAuto -KLaps=1 -KQuitAfter=45 -KQuality=$Q -KTime=0 -KTelemetry=perf_$N.csv "-ExecCmds=$X" -nosound -unattended -nosplash -nopause -stdout -log > $LOG 2>&1
$P/Tools/.venv/bin/python -c "
import re,statistics as st,sys
r=[tuple(map(float,m)) for m in re.findall(r\"KPERF game ([\d.]+) render ([\d.]+) gpu ([\d.]+) ms frame ([\d.]+)\",open(\"$LOG\",errors=\"ignore\").read())][8:]
print(\"%-12s n=%3d game %5.1f render %5.1f gpu %5.1f frame %5.1f ms = %4.1f fps\"%(\"$N\",len(r),*[st.median(c) for c in zip(*r)],1000/st.median(c[3] for c in r)) if r else \"$N VERI YOK\")"

# Cokme raporlayici %100 CPU ile asili kalmasin
pkill -f "CrashReport-UE-KapadokyaTuru" || true
