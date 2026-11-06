#!/bin/bash
pkill -f UnrealTraceServer 2>/dev/null
# Bolge bolge GPU olcumu (en fazla ~2.5 dk, sessiz).
# Kullanim: Tools/prof.sh ad kalite "r.A=0;r.B=1" [ResX ResY]
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
N=$1; Q=${2:-0}; X=${3:-nop=0}; RX=${4:-1600}; RY=${5:-900}; LOG=$P/Saved/prof_$N.log; export TAIL; rm -f $P/Saved/prof_$N.csv
perl -e "alarm shift; exec @ARGV" 290 $E/Engine/Binaries/Mac/UnrealEditor $P/KapadokyaTuru.uproject -game ${MODE:--windowed} -ResX=$RX -ResY=$RY -KAuto -KLaps=1 -KQuitAfter=${DUR:-62} -KQuality=$Q -KTime=0 -KTelemetry=prof_$N.csv "-KCVars=$X" -KProfileAt=${PROFAT:--1} -KCsvAt=${CSVAT:--1} -KHitch -KRaceShots=12,27,42,57 -KShotTag=prof_$N -KJumps=${JUMPS:-0.24,0.50,0.80} -KJumpEvery=${JE:-15} -nosound -unattended -nosplash -nopause -stdout -log > $LOG 2>&1
$P/Tools/.venv/bin/python - "$N" "$LOG" <<'PY'
import re,statistics as st,sys
n,log=sys.argv[1:]
r=[tuple(map(float,m)) for m in re.findall(r"KPERF game ([\d.]+) render ([\d.]+) gpu ([\d.]+) ms frame ([\d.]+)",open(log,errors="ignore").read())]
if len(r)<20: print(n,"VERI YOK",len(r)); sys.exit()
z=[r[6:14],r[20:29],r[35:44],r[50:59]]
m=lambda s,i: st.median(c[i] for c in s) if s else 0
fr=[c[3] for c in r[6:]]
import os
TL=int(os.environ.get("TAIL","0"))
if TL: tl=[c[3] for c in r[-TL:]]; print("   SICAK son %d sn: medyan %.1f ms = %.0f fps, en kotu %%10: %.0f ms"%(TL,st.median(tl),1000/st.median(tl),sorted(tl)[int(len(tl)*.9)]))
print("%-14s frame %5.1f ms (%4.1f fps) gpu %5.1f game %4.1f | bolge fps: %s | en kotu %%5: %.0f ms"%(n,st.median(fr),1000/st.median(fr),m(r[6:],2),m(r[6:],0)," ".join("%.0f"%(1000/m(s,3)) for s in z if s),sorted(fr)[int(len(fr)*.95)]))
PY
grep KHITCH $LOG | sed "s/.*KHITCH/  /"

# Cokme raporlayici %100 CPU ile asili kalmasin
pkill -f "CrashReport-UE-KapadokyaTuru" || true
