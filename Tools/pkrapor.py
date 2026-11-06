#!/usr/bin/env python3
# Tools/pkrapor.py ad : paket testi ozeti ve kare sayfasi
import csv,os,re,statistics as st,sys,glob
from PIL import Image
n=sys.argv[1]
C=os.path.expanduser("~/Library/Containers/com.YourCompany.KapadokyaTuru/Data/Library/Application Support/Epic/KapadokyaTuru/Saved")
r=list(csv.DictReader(open(f"{C}/pk_{n}.csv")));f=[float(x['fps']) for x in r]
print("kayit",len(f),"medyan",st.median(f),"ilk60",st.median(f[:60]),"son60",st.median(f[-60:]),"en kotu %5",sorted(f)[len(f)//20],"km",r[-1]['total_km'],"dusme",r[-1]['crashes'])
print("fps:",' '.join("%.0f"%x for x in f[4::10]))
h=[list(map(float,re.search(r'n (\d+) p50 ([\d.]+) p95 ([\d.]+) p99 ([\d.]+) max ([\d.]+) over50 (\d+) over100 (\d+)',l).groups())) for l in open(C+'/khitch.txt')]
print("p50:",' '.join("%.0f"%x[1] for x in h));print("p99:",' '.join("%.0f"%x[3] for x in h));print("50ms+",sum(x[5] for x in h),"100ms+",sum(x[6] for x in h),"/ kare",sum(x[0] for x in h))
fs=sorted(glob.glob(f"{C}/KShots/pk_{n}_r*.png"))[:4]
W=Image.new("RGB",(960*2,540*2))
for i,p in enumerate(fs): W.paste(Image.open(p).convert("RGB").resize((960,540)),((i%2)*960,(i//2)*540))
W.save(f"Saved/{n}_sheet.jpg",quality=88)
