#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, sys, urllib.request, urllib.parse

URL = RADARR_URL
KEY = RADARR_KEY
PROFILE = 6          # Any HD
ROOT = "/movies"
HDRS = {"X-Api-Key": KEY, "Content-Type": "application/json"}

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers=HDRS, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# (title, year) — year used to disambiguate
MOVIES = [
    # Lord of the Rings (and related)
    ("The Lord of the Rings: The Fellowship of the Ring", 2001),
    ("The Lord of the Rings: The Two Towers", 2002),
    ("The Lord of the Rings: The Return of the King", 2003),
    ("The Hobbit: An Unexpected Journey", 2012),
    ("The Hobbit: The Desolation of Smaug", 2013),
    ("The Hobbit: The Battle of the Five Armies", 2014),
    ("The Lord of the Rings: The War of the Rohirrim", 2024),
    # Star Wars (films)
    ("Star Wars: Episode I - The Phantom Menace", 1999),
    ("Star Wars: Episode II - Attack of the Clones", 2002),
    ("Star Wars: Episode III - Revenge of the Sith", 2005),
    ("Star Wars", 1977),  # A New Hope
    ("The Empire Strikes Back", 1980),
    ("Return of the Jedi", 1983),
    ("Star Wars: The Force Awakens", 2015),
    ("Star Wars: The Last Jedi", 2017),
    ("Star Wars: The Rise of Skywalker", 2019),
    ("Rogue One: A Star Wars Story", 2016),
    ("Solo: A Star Wars Story", 2018),
    ("Star Wars: The Clone Wars", 2008),
    # James Bond (Eon, 25)
    ("Dr. No", 1962),
    ("From Russia with Love", 1963),
    ("Goldfinger", 1964),
    ("Thunderball", 1965),
    ("You Only Live Twice", 1967),
    ("On Her Majesty's Secret Service", 1969),
    ("Diamonds Are Forever", 1971),
    ("Live and Let Die", 1973),
    ("The Man with the Golden Gun", 1974),
    ("The Spy Who Loved Me", 1977),
    ("Moonraker", 1979),
    ("For Your Eyes Only", 1981),
    ("Octopussy", 1983),
    ("A View to a Kill", 1985),
    ("The Living Daylights", 1987),
    ("Licence to Kill", 1989),
    ("GoldenEye", 1995),
    ("Tomorrow Never Dies", 1997),
    ("The World Is Not Enough", 1999),
    ("Die Another Day", 2002),
    ("Casino Royale", 2006),
    ("Quantum of Solace", 2008),
    ("Skyfall", 2012),
    ("Spectre", 2015),
    ("No Time to Die", 2021),
    # Indiana Jones (5)
    ("Raiders of the Lost Ark", 1981),
    ("Indiana Jones and the Temple of Doom", 1984),
    ("Indiana Jones and the Last Crusade", 1989),
    ("Indiana Jones and the Kingdom of the Crystal Skull", 2008),
    ("Indiana Jones and the Dial of Destiny", 2023),
]

existing = {m["tmdbId"] for m in api("/api/v3/movie")}
added, skipped, failed = [], [], []

for title, year in MOVIES:
    try:
        term = urllib.parse.quote(title)
        results = api(f"/api/v3/movie/lookup?term={term}")
        if not results:
            failed.append((title, year, "no lookup result")); continue
        # best match: exact year, else closest year, else first
        cand = sorted(results, key=lambda r: abs((r.get("year") or 0) - year))
        best = next((r for r in cand if r.get("year") == year), cand[0])
        tmdb = best["tmdbId"]
        chosen = f'{best["title"]} ({best.get("year")})'
        if tmdb in existing:
            skipped.append((chosen, "already in library")); continue
        payload = dict(best)
        payload["qualityProfileId"] = PROFILE
        payload["rootFolderPath"] = ROOT
        payload["monitored"] = True
        payload["addOptions"] = {"searchForMovie": True}
        res = api("/api/v3/movie", method="POST", body=payload)
        existing.add(tmdb)
        flag = "" if best.get("year") == year else f"  [year {best.get('year')} vs req {year}]"
        added.append((chosen, flag))
    except urllib.error.HTTPError as e:
        failed.append((title, year, f"HTTP {e.code}: {e.read().decode()[:120]}"))
    except Exception as e:
        failed.append((title, year, str(e)[:120]))

print(f"\n=== ADDED ({len(added)}) ===")
for c, f in added: print(" +", c, f)
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for c, why in skipped: print(" =", c, "-", why)
print(f"\n=== FAILED ({len(failed)}) ===")
for t, y, why in failed: print(" !", t, y, "-", why)
