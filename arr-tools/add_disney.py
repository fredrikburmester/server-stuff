#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.parse, urllib.error

URL = RADARR_URL
KEY = RADARR_KEY
PROFILE = 6
ROOT = "/movies"
HDRS = {"X-Api-Key": KEY, "Content-Type": "application/json"}

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers=HDRS, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

CANON = [
    ("Snow White and the Seven Dwarfs",1937),("Pinocchio",1940),("Fantasia",1940),
    ("Dumbo",1941),("Bambi",1942),("Saludos Amigos",1942),("The Three Caballeros",1944),
    ("Make Mine Music",1946),("Fun and Fancy Free",1947),("Melody Time",1948),
    ("The Adventures of Ichabod and Mr. Toad",1949),("Cinderella",1950),
    ("Alice in Wonderland",1951),("Peter Pan",1953),("Lady and the Tramp",1955),
    ("Sleeping Beauty",1959),("One Hundred and One Dalmatians",1961),
    ("The Sword in the Stone",1963),("The Jungle Book",1967),("The Aristocats",1970),
    ("Robin Hood",1973),("The Many Adventures of Winnie the Pooh",1977),("The Rescuers",1977),
    ("The Fox and the Hound",1981),("The Black Cauldron",1985),("The Great Mouse Detective",1986),
    ("Oliver & Company",1988),("The Little Mermaid",1989),("The Rescuers Down Under",1990),
    ("Beauty and the Beast",1991),("Aladdin",1992),("The Lion King",1994),("Pocahontas",1995),
    ("The Hunchback of Notre Dame",1996),("Hercules",1997),("Mulan",1998),("Tarzan",1999),
    ("Fantasia 2000",1999),("Dinosaur",2000),("The Emperor's New Groove",2000),
    ("Atlantis: The Lost Empire",2001),("Lilo & Stitch",2002),("Treasure Planet",2002),
    ("Brother Bear",2003),("Home on the Range",2004),("Chicken Little",2005),
    ("Meet the Robinsons",2007),("Bolt",2008),("The Princess and the Frog",2009),
    ("Tangled",2010),("Winnie the Pooh",2011),("Wreck-It Ralph",2012),("Frozen",2013),
    ("Big Hero 6",2014),("Zootopia",2016),("Moana",2016),("Ralph Breaks the Internet",2018),
    ("Frozen II",2019),("Raya and the Last Dragon",2021),("Encanto",2021),
    ("Strange World",2022),("Wish",2023),("Moana 2",2024),
]
PIXAR = [
    ("Toy Story",1995),("A Bug's Life",1998),("Toy Story 2",1999),("Monsters, Inc.",2001),
    ("Finding Nemo",2003),("The Incredibles",2004),("Cars",2006),("Ratatouille",2007),
    ("WALL-E",2008),("Up",2009),("Toy Story 3",2010),("Cars 2",2011),("Brave",2012),
    ("Monsters University",2013),("Inside Out",2015),("The Good Dinosaur",2015),
    ("Finding Dory",2016),("Cars 3",2017),("Coco",2017),("Incredibles 2",2018),
    ("Toy Story 4",2019),("Onward",2020),("Soul",2020),("Luca",2021),("Turning Red",2022),
    ("Lightyear",2022),("Elemental",2023),("Inside Out 2",2024),
]
REMAKES = [
    ("101 Dalmatians",1996),("102 Dalmatians",2000),("Alice in Wonderland",2010),
    ("Maleficent",2014),("Cinderella",2015),("The Jungle Book",2016),("Pete's Dragon",2016),
    ("Beauty and the Beast",2017),("Christopher Robin",2018),("Dumbo",2019),("Aladdin",2019),
    ("The Lion King",2019),("Maleficent: Mistress of Evil",2019),("Lady and the Tramp",2019),
    ("Mulan",2020),("Cruella",2021),("Pinocchio",2022),("Peter Pan & Wendy",2023),
    ("The Little Mermaid",2023),("Snow White",2025),
]
CLASSIC = [
    ("Mary Poppins",1964),("Mary Poppins Returns",2018),("Bedknobs and Broomsticks",1971),
    ("The Parent Trap",1961),("The Parent Trap",1998),("Swiss Family Robinson",1960),
    ("Pollyanna",1960),("The Absent-Minded Professor",1961),("Old Yeller",1957),
    ("The Love Bug",1968),("Tron",1982),("Tron: Legacy",2010),("Honey, I Shrunk the Kids",1989),
    ("The Rocketeer",1991),("Enchanted",2007),("Holes",2003),
    ("National Treasure",2004),("National Treasure: Book of Secrets",2007),
    ("Pirates of the Caribbean: The Curse of the Black Pearl",2003),
    ("Pirates of the Caribbean: Dead Man's Chest",2006),
    ("Pirates of the Caribbean: At World's End",2007),
    ("Pirates of the Caribbean: On Stranger Tides",2011),
    ("Pirates of the Caribbean: Dead Men Tell No Tales",2017),
]
GROUPS = [("Animated Canon",CANON),("Pixar",PIXAR),("Live-action remakes",REMAKES),("Classic live-action",CLASSIC)]

existing = {m["tmdbId"] for m in api("/api/v3/movie")}
added, skipped, failed = [], [], []

for gname, lst in GROUPS:
    for title, year in lst:
        try:
            term = urllib.parse.quote(title)
            results = api(f"/api/v3/movie/lookup?term={term}")
            if not results:
                failed.append((gname,title,year,"no lookup result")); continue
            cand = sorted(results, key=lambda r: abs((r.get("year") or 0) - year))
            best = next((r for r in cand if r.get("year") == year), cand[0])
            tmdb = best["tmdbId"]
            chosen = f'{best["title"]} ({best.get("year")})'
            if tmdb in existing:
                skipped.append((gname,chosen,"already in library")); continue
            payload = dict(best)
            payload["qualityProfileId"] = PROFILE
            payload["rootFolderPath"] = ROOT
            payload["monitored"] = True
            payload["addOptions"] = {"searchForMovie": True}
            api("/api/v3/movie", method="POST", body=payload)
            existing.add(tmdb)
            flag = "" if best.get("year") == year else f"  [year {best.get('year')} vs req {year}]"
            added.append((gname,chosen,flag))
        except urllib.error.HTTPError as e:
            failed.append((gname,title,year,f"HTTP {e.code}: {e.read().decode()[:120]}"))
        except Exception as e:
            failed.append((gname,title,year,str(e)[:120]))

print(f"\n=== ADDED ({len(added)}) ===")
for g,c,f in added: print(f" + [{g}] {c}{f}")
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for g,c,why in skipped: print(f" = [{g}] {c} - {why}")
print(f"\n=== FAILED ({len(failed)}) ===")
for g,t,y,why in failed: print(f" ! [{g}] {t} {y} - {why}")
