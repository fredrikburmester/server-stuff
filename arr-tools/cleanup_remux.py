#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.error

def api(base,key,path,method="GET",body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(base+path,data=data,
        headers={"X-Api-Key":key,"Content-Type":"application/json"},method=method)
    with urllib.request.urlopen(req,timeout=60) as r:
        t=r.read().decode(); return json.loads(t) if t else None

def get_all_queue(base,key,include):
    recs=[]; page=1
    while True:
        d=api(base,key,f"/api/v3/queue?page={page}&pageSize=250&{include}")
        rs=d.get("records",[]) if isinstance(d,dict) else d
        recs+=rs
        if not isinstance(d,dict) or page*d.get("pageSize",250)>=d.get("totalRecords",len(recs)) or not rs:
            break
        page+=1
    return recs

def qname(r):
    return ((r.get("quality") or {}).get("quality",{}) or {}).get("name","") or ""

# ---------- RADARR ----------
RB=RADARR_URL; RK=RADARR_KEY
q=get_all_queue(RB,RK,"includeMovie=true")
remux=[r for r in q if "remux" in qname(r).lower()]
ids=[r["id"] for r in remux]
movie_ids=sorted({r["movieId"] for r in remux if r.get("movieId")})
print(f"RADARR queue total={len(q)}  remux to remove={len(ids)}  movies to re-search={len(movie_ids)}")
# bulk remove + blocklist in chunks
for i in range(0,len(ids),100):
    chunk=ids[i:i+100]
    api(RB,RK,"/api/v3/queue/bulk?removeFromClient=true&blocklist=true&skipRedownload=true",
        method="DELETE",body={"ids":chunk})
    print(f"  removed+blocklisted {len(chunk)} items")
# trigger fresh search now that Remux is disallowed
if movie_ids:
    for i in range(0,len(movie_ids),100):
        chunk=movie_ids[i:i+100]
        api(RB,RK,"/api/v3/command",method="POST",body={"name":"MoviesSearch","movieIds":chunk})
        print(f"  triggered MoviesSearch for {len(chunk)} movies")

# ---------- SONARR ----------
SB=SONARR_URL; SK=SONARR_KEY
sq=get_all_queue(SB,SK,"includeSeries=true")
sremux=[r for r in sq if "remux" in qname(r).lower()]
sids=[r["id"] for r in sremux]
series_ids=sorted({r["seriesId"] for r in sremux if r.get("seriesId")})
print(f"SONARR queue total={len(sq)}  remux to remove={len(sids)}  series to re-search={len(series_ids)}")
for i in range(0,len(sids),100):
    chunk=sids[i:i+100]
    api(SB,SK,"/api/v3/queue/bulk?removeFromClient=true&blocklist=true&skipRedownload=true",
        method="DELETE",body={"ids":chunk})
    print(f"  removed+blocklisted {len(chunk)} items")
for sid in series_ids:
    api(SB,SK,"/api/v3/command",method="POST",body={"name":"SeriesSearch","seriesId":sid})
if series_ids: print(f"  triggered SeriesSearch for {len(series_ids)} series")
print("DONE")
