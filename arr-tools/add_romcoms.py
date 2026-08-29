#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY
import json, urllib.request, urllib.parse, urllib.error
URL=RADARR_URL; KEY=RADARR_KEY
PROFILE=6; ROOT="/movies"; HDRS={"X-Api-Key":KEY,"Content-Type":"application/json"}
def api(path, method="GET", body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(URL+path,data=data,headers=HDRS,method=method)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
MOVIES=[
 ("How to Lose a Guy in 10 Days",2003),
 ("The Princess Diaries",2001),
 ("The Notebook",2004),
 ("She's All That",1999),
 ("500 Days of Summer",2009),
 ("A Cinderella Story",2004),
 ("Love, Rosie",2014),
 ("Only You",1994),
 ("Hannah Montana: The Movie",2009),
]
# titles whose text search matches junk -> pin by TMDB id
OVERRIDES={"Only You":"tmdb:9058"}  # plain search hits several same-titled films
existing={m["tmdbId"] for m in api("/api/v3/movie")}
added,skipped,failed=[],[],[]
for title,year in MOVIES:
    try:
        term=OVERRIDES.get(title,title)
        results=api(f"/api/v3/movie/lookup?term={urllib.parse.quote(term)}")
        if not results: failed.append((title,year,"no lookup result")); continue
        cand=sorted(results,key=lambda r:abs((r.get("year") or 0)-year))
        best=next((r for r in cand if r.get("year")==year),cand[0])
        tmdb=best["tmdbId"]; chosen=f'{best["title"]} ({best.get("year")})'
        if tmdb in existing: skipped.append((chosen,"already in library")); continue
        p=dict(best); p["qualityProfileId"]=PROFILE; p["rootFolderPath"]=ROOT
        p["monitored"]=True; p["minimumAvailability"]="released"; p["addOptions"]={"searchForMovie":True}
        api("/api/v3/movie",method="POST",body=p); existing.add(tmdb)
        flag="" if best.get("year")==year else f"  [year {best.get('year')} vs req {year}]"
        added.append((chosen,flag))
    except urllib.error.HTTPError as e: failed.append((title,year,f"HTTP {e.code}: {e.read().decode()[:120]}"))
    except Exception as e: failed.append((title,year,str(e)[:120]))
print(f"\n=== ADDED ({len(added)}) ===")
for c,f in added: print(" +",c,f)
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for c,w in skipped: print(" =",c,"-",w)
print(f"\n=== FAILED ({len(failed)}) ===")
for t,y,w in failed: print(" !",t,y,"-",w)
