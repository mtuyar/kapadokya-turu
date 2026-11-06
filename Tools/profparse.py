#!/usr/bin/env python3
# ProfileGPU tablosunu okur: Tools/profparse.py Saved/prof_x.log [esik_ms] [maks_derinlik]
import re,sys
th=float(sys.argv[2]) if len(sys.argv)>2 else 0.35
maxd=int(sys.argv[3]) if len(sys.argv)>3 else 99
base=None
for l in open(sys.argv[1],errors='ignore'):
    if 'LogRHI' not in l or '┃' not in l: continue
    p=l.rstrip('\n').split('┃')
    if len(p)<5: continue
    t=re.findall(r'([\d.]+) ms',p[1]); i=re.findall(r'([\d.]+) ms',p[2])
    if not t or not i: continue
    ex,inc=float(t[0]),float(i[0]); nm=p[3].rstrip()
    d=len(nm)-len(nm.lstrip())
    if base is None: base=d
    if inc>=th and (d-base)//3<=maxd:
        print("%6.2f %6.2f  %s"%(inc,ex,nm[base:][:80]))
