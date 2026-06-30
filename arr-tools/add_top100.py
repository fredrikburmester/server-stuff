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
 ("The Shawshank Redemption",1994),("The Godfather",1972),("The Dark Knight",2008),
 ("The Godfather Part II",1974),("12 Angry Men",1957),
 ("The Lord of the Rings: The Return of the King",2003),("Schindler's List",1993),
 ("Pulp Fiction",1994),("The Lord of the Rings: The Fellowship of the Ring",2001),
 ("The Good, the Bad and the Ugly",1966),("Forrest Gump",1994),
 ("The Lord of the Rings: The Two Towers",2002),("Fight Club",1999),("Inception",2010),
 ("The Empire Strikes Back",1980),("The Matrix",1999),("Goodfellas",1990),
 ("One Flew Over the Cuckoo's Nest",1975),("Se7en",1995),("Seven Samurai",1954),
 ("Interstellar",2014),("It's a Wonderful Life",1946),("The Silence of the Lambs",1991),
 ("Saving Private Ryan",1998),("City of God",2002),("Life Is Beautiful",1997),
 ("The Green Mile",1999),("Star Wars",1977),("Terminator 2: Judgment Day",1991),
 ("Back to the Future",1985),("Spirited Away",2001),("The Pianist",2002),("Psycho",1960),
 ("Parasite",2019),("Léon: The Professional",1994),("The Lion King",1994),("Gladiator",2000),
 ("American History X",1998),("The Departed",2006),("The Usual Suspects",1995),
 ("The Prestige",2006),("Whiplash",2014),("Casablanca",1942),("Harakiri",1962),
 ("The Intouchables",2011),("Modern Times",1936),("Once Upon a Time in the West",1968),
 ("Rear Window",1954),("Alien",1979),("City Lights",1931),("Cinema Paradiso",1988),
 ("Apocalypse Now",1979),("Memento",2000),("Raiders of the Lost Ark",1981),
 ("Django Unchained",2012),("WALL-E",2008),("The Lives of Others",2006),
 ("Sunset Boulevard",1950),("Paths of Glory",1957),("The Shining",1980),
 ("The Great Dictator",1940),("Avengers: Infinity War",2018),
 ("Witness for the Prosecution",1957),("Aliens",1986),
 ("Spider-Man: Across the Spider-Verse",2023),("American Beauty",1999),
 ("The Dark Knight Rises",2012),("Coco",2017),("Oldboy",2003),("Amadeus",1984),
 ("Toy Story",1995),("Braveheart",1995),("Das Boot",1981),("Avengers: Endgame",2019),
 ("Inglourious Basterds",2009),("Princess Mononoke",1997),
 ("Once Upon a Time in America",1984),("Good Will Hunting",1997),("Your Name",2016),
 ("3 Idiots",2009),("Singin' in the Rain",1952),("Requiem for a Dream",2000),
 ("Toy Story 3",2010),("High and Low",1963),("Return of the Jedi",1983),
 ("Capernaum",2018),("2001: A Space Odyssey",1968),("Reservoir Dogs",1992),
 ("Citizen Kane",1941),("North by Northwest",1959),("Vertigo",1958),("M",1931),
 ("Lawrence of Arabia",1962),("The Hunt",2012),("Double Indemnity",1944),
 ("Bicycle Thieves",1948),("Dangal",2016),("Amélie",2001),("A Clockwork Orange",1971),
 ("Like Stars on Earth",2007),
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
