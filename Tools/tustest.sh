#!/bin/bash
pkill -f UnrealTraceServer 2>/dev/null
# Gercek tus testi: tuslar SADECE oyun ondeyse gonderilir, sonda hepsi birakilir. En fazla ~75 sn, sessiz.
P=/Volumes/Unreal/Projeler/KapadokyaTuru
A=$P/Dist/Mac/KapadokyaTuru-Mac-Shipping.app/Contents/MacOS/KapadokyaTuru-Mac-Shipping
S="$HOME/Library/Containers/com.YourCompany.KapadokyaTuru/Data/Library/Application Support/Epic/KapadokyaTuru/Saved"
rm -f "$S/pk_key.csv" "$S"/KShots/view_*.png
perl -e 'alarm shift; exec @ARGV' 110 "$A" -windowed -ResX=1600 -ResY=900 -KQuality=0 -KTime=${KT:-0} -KTelemetry=pk_key.csv -KQuitAfter=${QA:-45} -KViewShots=${VS:-14,32,44,50} -nosound -nosplash -nopause > /dev/null 2>&1 &
G=$!
front(){ osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>&1; }
release(){ osascript -e 'tell application "System Events"' -e 'key up "w"' -e 'key up "a"' -e 'key up "d"' -e 'end tell' >/dev/null 2>&1; }
trap release EXIT
send(){ # tek satir AppleScript, oyun onde degilse gondermez
  f=$(front); case "$f" in *Kapadokya*) ;; *) echo "IPTAL: onde '$f'"; release; kill $G 2>/dev/null; exit 3;; esac
  osascript -e "tell application \"System Events\" to $1" 2>&1 | head -2
}
for i in $(seq 1 15); do osascript -e 'tell application "System Events" to set frontmost of (first process whose name contains "Kapadokya") to true' >/dev/null 2>&1; sleep 1; case "$(front)" in *Kapadokya*) break;; esac; done
echo "onde: $(front)"; sleep 8
echo "Enter"; send 'key code 36'
sleep 8
echo "W basili"; send 'key down "w"'; sleep 8
echo "D"; send 'key down "d"'; sleep 1.5; send 'key up "d"'; sleep 3
echo "A"; send 'key down "a"'; sleep 1.5; send 'key up "a"'; sleep 2
echo "E,E,Q,C"; send 'keystroke "e"'; sleep .5; send 'keystroke "e"'; sleep .5; send 'keystroke "q"'; sleep 1; send 'keystroke "c"'; sleep 3
release
wait $G; echo "oyun cikisi $?"
