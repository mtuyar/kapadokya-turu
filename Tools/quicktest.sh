#!/bin/bash
# En fazla 5 dk: peloton bolgelere isinlanir, sonda bitis cizgisine atlar.
# Kullanim: Tools/quicktest.sh etiket [kalite] [zaman]
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
TAG=$1; Q=${2:-1}; T=${3:-0}; LOG=$P/Saved/$TAG.log
perl -e "alarm shift; exec @ARGV" 290 $E/Engine/Binaries/Mac/UnrealEditor $P/KapadokyaTuru.uproject -game -windowed -ResX=1600 -ResY=900 -KAuto -KLaps=1 -KQuit -KQuitAfter=160 -KQuality=$Q -KTime=$T -KTelemetry=$TAG.csv -KJumps=0.10,0.24,0.34,0.50,0.66,0.80,0.985 -KJumpEvery=18 -KRaceShots=8,15,33,51,69,87,105,123,131 -KShotTag=$TAG $4 $5 -nosound -unattended -nosplash -nopause -stdout -log > $LOG 2>&1
echo "exit $?"
grep -E "Fatal|appError|Failed to compile" $LOG | cut -c1-200 | sort -u | head
grep -E "KJUMP" $LOG | cut -c30-90
$P/Tools/.venv/bin/python - "$TAG" <<PY
import csv,glob,statistics as st,sys
from PIL import Image
tag=sys.argv[1]; P="/Volumes/Unreal/Projeler/KapadokyaTuru/Saved/"
r=list(csv.DictReader(open(P+tag+".csv")))
prev=0
for x in r:
    if int(x["crashes"])!=prev:
        print("DUSME t",x["t"],"km",x["total_km"],"v",x["speed_kmh"],"lean",x["lean_deg"],"lat",x["lateral_m"]); prev=int(x["crashes"])
f=[float(x["fps"]) for x in r]
print("fps medyan",st.median(f),"min",min(f),"maks",max(f),"| maks hiz",max(float(x["speed_kmh"]) for x in r),"maks yanal",max(abs(float(x["lateral_m"])) for x in r),"| son km",r[-1]["total_km"],"sira",r[-1]["pos"],"dusme",r[-1]["crashes"])
fs=sorted(glob.glob(P+"KShots/"+tag+"_r*.png"))
W=Image.new("RGB",(640*3,360*3))
for i,fn in enumerate(fs[:9]): W.paste(Image.open(fn).convert("RGB").resize((640,360)),((i%3)*640,(i//3)*360))
W.save(P+tag+"_sheet.jpg",quality=88); print("kare",len(fs))
PY

# Cokme raporlayici %100 CPU ile asili kalmasin
pkill -f "CrashReport-UE-KapadokyaTuru" || true
