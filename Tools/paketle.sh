#!/bin/bash
# Shipping paket: Dist/ altina tek basina calisan uygulama uretir.
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
$E/Engine/Build/BatchFiles/RunUAT.sh BuildCookRun -project=$P/KapadokyaTuru.uproject -noP4 -platform=Mac -clientconfig=Shipping -build -cook -stage -pak -iostore -package -archive -archivedirectory=$P/Dist -utf8output -unattended -nocompileeditor > $P/Saved/paket.log 2>&1
echo "PAKET CIKIS $?"
