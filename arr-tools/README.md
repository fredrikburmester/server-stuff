# arr-tools

Small Python scripts for bulk-managing **Radarr** (movies) and **Sonarr** (TV)
over their v3 REST APIs — bulk-adding libraries by list, and tuning quality
profiles / file sizes.

No dependencies beyond the Python 3 standard library.

## Setup

```bash
cp .env.example .env      # then edit .env with your real API keys
```

Credentials live in `.env` (gitignored). All scripts read them via `arrlib.py`,
so **no keys are hardcoded**. API key: Radarr/Sonarr → Settings → General → API Key.

Run scripts from inside this folder (so `import arrlib` resolves):

```bash
cd arr-tools
python3 add_top100.py
```

## How adding works

Each `add_*.py` holds a `(title, year)` list. For every entry it:

1. hits `/movie/lookup` (or `/series/lookup`) with the title,
2. picks the best match — exact year first, else nearest year,
3. skips it if already in the library (dedup by TMDB/TVDB id),
4. adds it with the **Any HD** profile (id 6) + root folder, monitored,
   and triggers a search.

Re-running is safe — anything already present is skipped. Years disambiguate
remakes (e.g. *The Lion King* 1994 vs 2019).

> **Gotcha:** a few titles break Radarr's text search (e.g. `WALL-E` — the hyphen
> matches junk like *"Eiger: Wall of death"*). For those, add by TMDB id instead:
> `lookup?term=tmdb:10681`. See the `OVERRIDES` map in `add_boxoffice.py`.

## Scripts

### Library adders
| Script | Adds |
|---|---|
| `add_movies.py`    | LOTR · Star Wars (films) · all 25 Bond · Indiana Jones |
| `add_shows.py`     | Star Wars TV series (Mandalorian, Andor, Clone Wars, …) |
| `add_disney.py`    | Disney animated canon · Pixar · live-action remakes · classic live-action |
| `add_top100.py`    | IMDb Top 100 |
| `add_boxoffice.py` | Top-10 highest-grossing films per year, 2000–2025 (has TMDB-id `OVERRIDES`) |
| `add_movies2.py`   | Ad-hoc movie batch (template — edit the `MOVIES` list) |
| `add_shows2.py`    | Ad-hoc TV batch (template — edit the `SHOWS` list) |

To add your own list, copy `add_movies2.py` / `add_shows2.py` and edit the list.

### Maintenance / tuning
| Script | Does |
|---|---|
| `fix_profiles.py`   | Disables **Remux / 2160p / BR-DISK / Raw-HD** in the *Any HD* profile (id 6) on both apps, so huge untouched-Blu-ray rips aren't grabbed. Cutoff → Bluray-1080p. |
| `cap_sizes.py`      | Radarr quality definitions: sets size **preferred ≈ 50 MB/min (~5.8 GB/2 h)** and **max 100 MB/min** so movies bias toward lean encodes. Sizes are MB-per-minute, scaled by runtime. |
| `cleanup_remux.py`  | Removes + blocklists in-progress **Remux** downloads in both queues and re-searches (re-grabs as Bluray-1080p). |
| `cleanup_sonarr.py` | Robust Sonarr-only remux purge — dedupes the queue by `downloadId` (Sonarr queue entries are per-episode; one download spans many). Use if `cleanup_remux.py` 404s on Sonarr. |

## Notes
- Quality profile **Any HD** = id 6; roots are `/movies` (Radarr) and `/tv` (Sonarr).
- `arrlib.py` also exposes a generic `api(base, key, path, ...)` helper for new scripts.
