#!/bin/bash
# Kapadokya Turu: cift tiklayip oyna. 'Unreal' diski takili olmali.
P="/Volumes/Unreal/Projeler/KapadokyaTuru"
A="$P/Dist/Mac/KapadokyaTuru-Mac-Shipping.app/Contents/MacOS/KapadokyaTuru-Mac-Shipping"
E="/Volumes/Unreal/EpicGames/UE_5.8/Engine/Binaries/Mac/UnrealEditor"
# Editor kullanimindan kalan iz sunucusu CPU yemesin
pkill -f UnrealTraceServer 2>/dev/null
ARGS="-windowed -ResX=1600 -ResY=900 -KQuality=0 -KTime=0 -nosplash"
if [ -x "$A" ]; then
  exec "$A" $ARGS
elif [ -x "$E" ]; then
  exec "$E" "$P/KapadokyaTuru.uproject" -game $ARGS
fi
echo "Oyun bulunamadi. 'Unreal' diskini takip yeniden dene."
read -r -p "Kapatmak icin Enter..."
exit 1
