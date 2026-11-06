#!/bin/bash
# Menu testi: tuslar SADECE oyun ondeyse gonderilir, sonda hepsi birakilir. En fazla ~75 sn, sessiz.
P=/Volumes/Unreal/Projeler/KapadokyaTuru
A=$P/Dist/Mac/KapadokyaTuru-Mac-Shipping.app/Contents/MacOS/KapadokyaTuru-Mac-Shipping
S="$HOME/Library/Containers/com.YourCompany.KapadokyaTuru/Data/Library/Application Support/Epic/KapadokyaTuru/Saved"
rm -f "$S/pk_menu.csv" "$S"/KShots/view_*.png
perl -e 'alarm shift; exec @ARGV' 80 "$A" -windowed -ResX=1600 -ResY=900 -KQuality=0 -KTime=${KT:-0} -KTelemetry=pk_menu.csv -KQuitAfter=15 -KViewShots=${VS:-17,27,38,54} -nosound -nosplash -nopause > /dev/null 2>&1 &
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
k(){ send "key code $1"; sleep .35; }
DOWN=125; UP=126; RIGHT=124; LEFT=123
echo "Gun isigi: ogle"; for x in 1 2 3 4; do k $DOWN; done; k $RIGHT; sleep 3
echo "Grafik: Yuksek"; k $DOWN; k $RIGHT; k $RIGHT; sleep 9
echo "Grafik: Dusuk"; k $LEFT; k $LEFT; sleep 5
echo "Gun batimi"; k $UP; k $RIGHT; sleep 3
echo "Yarisa basla"; for x in 1 2 3 4; do k $UP; done; k 36; sleep 8; send 'key down "w"'; sleep 14
release
wait $G; echo "oyun cikisi $?"
