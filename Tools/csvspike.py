#!/usr/bin/env python3
# Son CSV profilinde yavas ve hizli kareler arasinda en cok artan olcumler
import csv,glob,os,statistics as st
f=max(glob.glob('Saved/Profiling/CSV/*.csv'),key=os.path.getmtime)
rows=list(csv.reader(open(f,errors='ignore'))); h=rows[0]; d=[r for r in rows[1:] if len(r)==len(h)]
ft=h.index('FrameTime'); T=[float(r[ft]) for r in d]
med=st.median(T); slow=[r for r,t in zip(d,T) if t>max(30,med*1.6)]; fast=[r for r,t in zip(d,T) if t<=med*1.1]
print("kare",len(d),"medyan %.1f maks %.1f yavas %d"%(med,max(T),len(slow)))
out=[]
for i,n in enumerate(h):
    if not n.startswith(('Exclusive/','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime','PSO','Ticks','RHI/','Basic/')): continue
    try:
        a=st.mean(float(r[i]) for r in slow); b=st.mean(float(r[i]) for r in fast)
    except Exception: continue
    out.append((a-b,a,b,n))
for dv,a,b,n in sorted(out,reverse=True)[:16]: print("  +%6.2f yavas %7.2f hizli %7.2f %s"%(dv,a,b,n))
