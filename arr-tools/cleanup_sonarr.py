#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.error

SB=SONARR_URL; SK=SONARR_KEY
def api(path,method="GET",body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(SB+path,data=data,
        headers={"X-Api-Key":SK,"Content-Type":"application/json"},method=method)
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            t=r.read().decode(); return json.loads(t) if t else None
    except urllib.error.HTTPError as e:
        return {"__err":e.code}

def qname(r): return ((r.get("quality") or {}).get("quality",{}) or {}).get("name","") or ""

def fetch_remux():
    recs=[]; page=1
    while True:
        d=api(f"/api/v3/queue?page={page}&pageSize=250&includeSeries=true")
        rs=d.get("records",[]); recs+=rs
        if page*d.get("pageSize",250)>=d.get("totalRecords",0) or not rs: break
        page+=1
    return [r for r in recs if "remux" in qname(r).lower()]

remux=fetch_remux()
series_ids=sorted({r["seriesId"] for r in remux if r.get("seriesId")})
# one queue id per unique downloadId (removing it drops the whole grab)
seen=set(); unique_ids=[]
for r in remux:
    dl=r.get("downloadId") or r["id"]
    if dl in seen: continue
    seen.add(dl); unique_ids.append(r["id"])
print(f"SONARR remux queue entries={len(remux)}  unique downloads={len(unique_ids)}  series={len(series_ids)}")

removed=0
for i in range(0,len(unique_ids),50):
    chunk=unique_ids[i:i+50]
    res=api("/api/v3/queue/bulk?removeFromClient=true&blocklist=true&skipRedownload=true",
            method="DELETE",body={"ids":chunk})
    if isinstance(res,dict) and res.get("__err"):
        # fall back to one-by-one for this chunk
        for qid in chunk:
            r=api(f"/api/v3/queue/{qid}?removeFromClient=true&blocklist=true&skipRedownload=true",method="DELETE")
            if not (isinstance(r,dict) and r.get("__err")): removed+=1
    else:
        removed+=len(chunk)
    print(f"  processed {min(i+50,len(unique_ids))}/{len(unique_ids)} (removed so far ~{removed})")

for sid in series_ids:
    api("/api/v3/command",method="POST",body={"name":"SeriesSearch","seriesId":sid})
print(f"triggered SeriesSearch for {len(series_ids)} series")
print("DONE removed ~",removed)
