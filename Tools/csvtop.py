#!/usr/bin/env python3
# Son CsvProfile dosyasini ozetler
import csv,glob,os,statistics as st,sys
f=max(glob.glob('Saved/Profiling/CSV/*.csv'),key=os.path.getmtime)
rows=list(csv.reader(open(f,errors='ignore'))); h=rows[0]; d=[r for r in rows[1:] if len(r)==len(h)]
m={}
for i,n in enumerate(h):
    try: m[n]=st.mean(float(r[i]) for r in d)
    except: pass
print("  csv kare %d frame %.1f gt %.1f rt %.1f rhi %.1f gpu %.1f"%(len(d),m.get("FrameTime",0),m.get("GameThreadTime",0),m.get("RenderThreadTime",0),m.get('RHIThreadTime',0),m.get('GPUTime',0)))
t=sorted(((v,n) for n,v in m.items() if n.startswith('Exclusive/RenderThread/')),reverse=True)[:5]
print("  RT:"," ".join("%s=%.1f"%(n[23:],v) for v,n in t))
