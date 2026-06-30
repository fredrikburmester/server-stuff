#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.parse, urllib.error

URL = SONARR_URL
KEY = SONARR_KEY
PROFILE = 6          # Any HD
ROOT = "/tv"
HDRS = {"X-Api-Key": KEY, "Content-Type": "application/json"}

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers=HDRS, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# (title, year) for disambiguation
SHOWS = [
    ("The Mandalorian", 2019),
    ("The Book of Boba Fett", 2021),
    ("Obi-Wan Kenobi", 2022),
    ("Andor", 2022),
    ("Ahsoka", 2023),
    ("Star Wars: The Clone Wars", 2008),
    ("Star Wars Rebels", 2014),
    ("Star Wars: The Bad Batch", 2021),
    ("Star Wars Resistance", 2018),
    ("Star Wars: Visions", 2021),
    ("Star Wars: Tales of the Jedi", 2022),
    ("Star Wars: Tales of the Empire", 2024),
    ("Star Wars: Young Jedi Adventures", 2023),
    ("The Acolyte", 2024),
    ("Star Wars: Skeleton Crew", 2024),
    ("Star Wars: Droids", 1985),
    ("Star Wars: Ewoks", 1985),
]

existing = {s["tvdbId"] for s in api("/api/v3/series")}
added, skipped, failed = [], [], []

for title, year in SHOWS:
    try:
        term = urllib.parse.quote(title)
        results = api(f"/api/v3/series/lookup?term={term}")
        if not results:
            failed.append((title, year, "no lookup result")); continue
        cand = sorted(results, key=lambda r: abs((r.get("year") or 0) - year))
        best = next((r for r in cand if r.get("year") == year), cand[0])
        tvdb = best.get("tvdbId")
        chosen = f'{best["title"]} ({best.get("year")})'
        if not tvdb:
            failed.append((title, year, "no tvdbId")); continue
        if tvdb in existing:
            skipped.append((chosen, "already in library")); continue
        payload = dict(best)
        payload["qualityProfileId"] = PROFILE
        payload["rootFolderPath"] = ROOT
        payload["monitored"] = True
        payload["seasonFolder"] = True
        payload["addOptions"] = {"monitor": "all", "searchForMissingEpisodes": True}
        api("/api/v3/series", method="POST", body=payload)
        existing.add(tvdb)
        flag = "" if best.get("year") == year else f"  [year {best.get('year')} vs req {year}]"
        added.append((chosen, flag))
    except urllib.error.HTTPError as e:
        failed.append((title, year, f"HTTP {e.code}: {e.read().decode()[:140]}"))
    except Exception as e:
        failed.append((title, year, str(e)[:140]))

print(f"\n=== ADDED ({len(added)}) ===")
for c, f in added: print(" +", c, f)
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for c, why in skipped: print(" =", c, "-", why)
print(f"\n=== FAILED ({len(failed)}) ===")
for t, y, why in failed: print(" !", t, y, "-", why)
