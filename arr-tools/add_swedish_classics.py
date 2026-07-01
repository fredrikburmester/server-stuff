#!/usr/bin/env python3
"""Add Swedish children's/family film classics to Radarr (Astrid Lindgren et al.)."""
from arrlib import RADARR_URL, RADARR_KEY, api
import urllib.parse

PROFILE = 6        # Any HD
ROOT = "/movies"

# (title, year) — Swedish titles; year disambiguates films vs TV series
MOVIES = [
    # Pippi Långstrump
    ("Pippi Långstrump", 1969),
    ("Pippi Långstrump på de sju haven", 1970),
    ("På rymmen med Pippi Långstrump", 1970),
    ("Här kommer Pippi Långstrump", 1973),
    # Emil i Lönneberga
    ("Emil i Lönneberga", 1971),
    ("Nya hyss av Emil i Lönneberga", 1972),
    ("Emil och griseknoen", 1973),
    # Madicken
    ("Du är inte klok, Madicken", 1979),
    ("Madicken på Junibacken", 1980),
    # other Astrid Lindgren
    ("Bröderna Lejonhjärta", 1977),
    ("Ronja Rövardotter", 1984),
    ("Mio min Mio", 1987),
    ("Rasmus på luffen", 1981),
    ("Alla vi barn i Bullerbyn", 1986),
    ("Mer om oss barn i Bullerbyn", 1987),
    ("Lotta på Bråkmakargatan", 1992),
    ("Lotta 2 - Lotta flyttar hemifrån", 1993),
    ("Mästerdetektiven Blomkvist lever farligt", 1996),
    ("Kalle Blomkvist och Rasmus", 1997),
    # Vi på Saltkråkan films
    ("Tjorven, Båtsman och Moses", 1964),
    ("Tjorven och Skrållan", 1965),
    ("Tjorven och Mysak", 1966),
    ("Skrållan, Ruskprick och Knorrhane", 1967),
    # other Swedish children's/family classics
    ("Dunderklumpen!", 1974),
    ("Pelle Svanslös", 1981),
    ("Pelle Svanslös i Amerikatt", 1985),
    ("Karlsson på taket", 1974),
    ("Resan till Melonia", 1989),
    ("Agaton Sax och Byköpings gästabud", 1976),
]

existing = {m["tmdbId"] for m in api(RADARR_URL, RADARR_KEY, "/api/v3/movie")}
added, skipped, failed = [], [], []
for title, year in MOVIES:
    try:
        results = api(RADARR_URL, RADARR_KEY, f"/api/v3/movie/lookup?term={urllib.parse.quote(title)}")
        if not results:
            failed.append((title, year, "no lookup result")); continue
        cand = sorted(results, key=lambda r: abs((r.get("year") or 0) - year))
        best = next((r for r in cand if r.get("year") == year), cand[0])
        tmdb = best["tmdbId"]; chosen = f'{best["title"]} ({best.get("year")})'
        if tmdb in existing:
            skipped.append((chosen, "already in library")); continue
        p = dict(best); p["qualityProfileId"] = PROFILE; p["rootFolderPath"] = ROOT
        p["monitored"] = True; p["addOptions"] = {"searchForMovie": True}
        api(RADARR_URL, RADARR_KEY, "/api/v3/movie", method="POST", body=p); existing.add(tmdb)
        flag = "" if best.get("year") == year else f"  [yr {best.get('year')} vs {year}]"
        added.append((chosen, flag))
    except Exception as e:
        failed.append((title, year, str(e)[:100]))

print(f"\n=== ADDED ({len(added)}) ===")
for c, f in added: print(" +", c, f)
print(f"\n=== SKIPPED ({len(skipped)}) ===")
for c, w in skipped: print(" =", c, "-", w)
print(f"\n=== FAILED ({len(failed)}) ===")
for t, y, w in failed: print(" !", t, y, "-", w)
