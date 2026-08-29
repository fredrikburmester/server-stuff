#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.parse, urllib.error
URL=SONARR_URL; KEY=SONARR_KEY
PROFILE=6; ROOT="/tv"; HDRS={"X-Api-Key":KEY,"Content-Type":"application/json"}
def api(path, method="GET", body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(URL+path,data=data,headers=HDRS,method=method)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
SHOWS=[
 ("One Punch Man",2015),
]
existing={s["tvdbId"] for s in api("/api/v3/series")}
added,skipped,failed=[],[],[]
for title,year in SHOWS:
    try:
        results=api(f"/api/v3/series/lookup?term={urllib.parse.quote(title)}")
        if not results: failed.append((title,year,"no lookup result")); continue
        cand=sorted(results,key=lambda r:abs((r.get("year") or 0)-year))
        best=next((r for r in cand if r.get("year")==year),cand[0])
        tvdb=best.get("tvdbId"); chosen=f'{best["title"]} ({best.get("year")})'
        if not tvdb: failed.append((title,year,"no tvdbId")); continue
        if tvdb in existing: skipped.append((chosen,"already in library")); continue
        p=dict(best); p["qualityProfileId"]=PROFILE; p["rootFolderPath"]=ROOT
        p["monitored"]=True; p["seasonFolder"]=True; p["seriesType"]="anime"
        p["addOptions"]={"monitor":"firstSeason","searchForMissingEpisodes":True}
        api("/api/v3/series",method="POST",body=p); existing.add(tvdb)
        flag="" if best.get("year")==year else f"  [year {best.get('year')} vs req {year}]"
        added.append((chosen,flag))
    except urllib.error.HTTPError as e: failed.append((title,year,f"HTTP {e.code}: {e.read().decode()[:140]}"))
    except Exception as e: failed.append((title,year,str(e)[:140]))
print(f"\n=== ADDED ({len(added)}) ===")
for c,f in added: print(" +",c,f)
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for c,w in skipped: print(" =",c,"-",w)
print(f"\n=== FAILED ({len(failed)}) ===")
for t,y,w in failed: print(" !",t,y,"-",w)
