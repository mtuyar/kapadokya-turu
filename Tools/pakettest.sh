#!/bin/bash
pkill -f UnrealTraceServer 2>/dev/null
# Paketli oyunu olcer (sessiz, isinlamali, en fazla ~4.5 dk). Kullanim: Tools/pakettest.sh ad sure kalite
P=/Volumes/Unreal/Projeler/KapadokyaTuru; N=$1; D=${2:-150}; Q=${3:-0}
A=$P/Dist/Mac/KapadokyaTuru-Mac-Shipping.app/Contents/MacOS/KapadokyaTuru-Mac-Shipping
S="$HOME/Library/Containers/com.YourCompany.KapadokyaTuru/Data/Library/Application Support/Epic/KapadokyaTuru/Saved"
rm -f "$S/khitch.txt" "$S/pk_$N.csv"
perl -e "alarm shift; exec @ARGV" 280 "$A" -windowed -ResX=1600 -ResY=900 -KAuto -KLaps=1 -KQuitAfter=$D -KQuality=$Q -KTime=${KT:-0} -KTelemetry=pk_$N.csv -KHitch -KRaceShots=20,50,80,110 -KShotTag=pk_$N -KJumps=0.24,0.50,0.80,0.10,0.34,0.66 -KJumpEvery=${JE:-22} "-KCVars=${KV:-nop=0}" $EXTRA -nosound -unattended -nosplash -nopause > $P/Saved/pk_$N.out 2>&1
echo "cikis $?"
cat "$S/khitch.txt" 2>/dev/null | sed 's/KHITCH //'
$P/Tools/.venv/bin/python - "$S/pk_$N.csv" <<'PY'
import csv,statistics as st,sys
r=list(csv.DictReader(open(sys.argv[1])))
f=[float(x['fps']) for x in r]; t=f[-45:]
print("kayit",len(f),"medyan",st.median(f),"son45 medyan",st.median(t),"km",r[-1]['total_km'],"dusme",r[-1]['crashes'])
print(' '.join("%.0f"%x for x in f[4::6]))
PY
pkill -f "CrashReport-UE-KapadokyaTuru" || true
