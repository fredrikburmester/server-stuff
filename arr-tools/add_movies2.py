#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.parse, urllib.error
URL=RADARR_URL; KEY=RADARR_KEY
PROFILE=6; ROOT="/movies"; HDRS={"X-Api-Key":KEY,"Content-Type":"application/json"}
def api(path, method="GET", body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(URL+path,data=data,headers=HDRS,method=method)
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
MOVIES=[
 ("Toy Story",1995),("Toy Story 2",1999),("Batman Begins",2005),("The Dark Knight",2008),
 ("Jerry Maguire",1996),("Raiders of the Lost Ark",1981),("Obsessed",2009),
 ("Sentimental Value",2025),("The Housemaid",2025),("Wicked",2024),
 ("The Lord of the Rings: The Return of the King",2003),("Venom: Let There Be Carnage",2021),
 ("10 Things I Hate About You",1999),("American Gangster",2007),
 ("Spider-Man: Into the Spider-Verse",2018),("Mission: Impossible III",2006),
 ("Gladiator",2000),("Nobody",2021),("Transformers",2007),("2 Fast 2 Furious",2003),
 ("Finch",2021),("Star Wars: Episode II - Attack of the Clones",2002),("Sinners",2025),
 ("Casino Royale",2006),("Avicii: True Stories",2017),
]
existing={m["tmdbId"] for m in api("/api/v3/movie")}
added,skipped,failed=[],[],[]
for title,year in MOVIES:
    try:
        results=api(f"/api/v3/movie/lookup?term={urllib.parse.quote(title)}")
        if not results: failed.append((title,year,"no lookup result")); continue
        cand=sorted(results,key=lambda r:abs((r.get("year") or 0)-year))
        best=next((r for r in cand if r.get("year")==year),cand[0])
        tmdb=best["tmdbId"]; chosen=f'{best["title"]} ({best.get("year")})'
        if tmdb in existing: skipped.append((chosen,"already in library")); continue
        p=dict(best); p["qualityProfileId"]=PROFILE; p["rootFolderPath"]=ROOT
        p["monitored"]=True; p["addOptions"]={"searchForMovie":True}
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
