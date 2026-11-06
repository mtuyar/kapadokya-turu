#!/usr/bin/env python3
# Tools/sheet.py ad1 ad2 ... : prof kosularinin karelerini tek sayfada toplar (satir=kosu)
import glob,sys
from PIL import Image
P="/Volumes/Unreal/Projeler/KapadokyaTuru/Saved/"
n=sys.argv[1:]; W=Image.new("RGB",(480*4,270*len(n)))
for y,t in enumerate(n):
    for x,f in enumerate(sorted(glob.glob(P+"KShots/prof_"+t+"_r*.png"))[:4]):
        W.paste(Image.open(f).convert("RGB").resize((480,270)),(x*480,y*270))
W.save(P+"sheet_"+n[0]+".jpg",quality=88); print(P+"sheet_"+n[0]+".jpg")
