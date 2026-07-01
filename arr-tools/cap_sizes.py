#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.error

RB=RADARR_URL; RK=RADARR_KEY
def api(path,method="GET",body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(RB+path,data=data,
        headers={"X-Api-Key":RK,"Content-Type":"application/json"},method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        t=r.read().decode(); return json.loads(t) if t else None

# Cap movie size ~8GB for a typical 2h film. MB/min, scales w/ runtime.
PREF=45.0   # ~5.2 GB @115m  (target -> biases to lean encodes)
MAXV=70.0   # ~8.0 GB @115m  (hard cap -> rejects oversized grabs)

defs=api("/api/v3/qualitydefinition")
changed=[]
for d in defs:
    q=d['quality']['name']
    if any(x in q for x in ['720p','1080p']):  # all HD movie qualities
        d['minSize']=0
        d['preferredSize']=PREF
        d['maxSize']=MAXV
        api(f"/api/v3/qualitydefinition/{d['id']}",method="PUT",body=d)
        changed.append(q)
print("Updated (pref=%.0f max=%.0f MB/min):"%(PREF,MAXV))
for q in changed: print("  -",q)
print(f"\n~8.0 GB ceiling for a 115-min movie; scales with runtime.")
