#!/bin/bash
# Kullanim: Tools/shots.sh etiket "0.02,0.2" [kalite] [zaman] [ek argumanlar]
P=/Volumes/Unreal/Projeler/KapadokyaTuru; E=/Volumes/Unreal/EpicGames/UE_5.8
TAG=$1; LIST=$2; Q=${3:-1}; T=${4:-0}; shift 4
LOG=$P/Saved/shots_$TAG.log
perl -e "alarm shift; exec @ARGV" 1500 $E/Engine/Binaries/Mac/UnrealEditor $P/KapadokyaTuru.uproject -game -windowed -ResX=1600 -ResY=900 -KShots=$LIST -KShotTag=$TAG -KQuality=$Q -KTime=$T -nosound -unattended -nosplash -nopause -stdout -log "$@" > $LOG 2>&1
echo "exit $?"
grep -E "KSHOT|Fatal|Assertion failed|Mesh yok|LogRHI.*(Metal|SM6)|FeatureLevel|Nanite.*(Enabled|disabled)|PSO|Ensure condition" $LOG | cut -c1-200 | tail -30
