# server-stuff

Homelab server configs and operational tooling.

## Radarr / Sonarr management — use `arr-tools/`

When the user asks to **add movies or TV shows** to Radarr/Sonarr, **bulk-import a
list**, or **tune quality profiles / download sizes**, use the scripts in
[`arr-tools/`](arr-tools/) instead of hand-rolling API calls. They already handle
lookup, best-match-by-year, dedup against the existing library, the **Any HD**
profile (id 6), root folders (`/movies`, `/tv`), and search-on-add.

- Credentials load from `arr-tools/.env` (gitignored) via `arr-tools/arrlib.py` —
  **never hardcode API keys** in scripts or commit them. If `.env` is missing,
  copy `arr-tools/.env.example`.
- Run scripts from inside `arr-tools/` (so `import arrlib` resolves).
- **To add a new list:** copy `add_movies2.py` / `add_shows2.py`, edit the
  `(title, year)` list, run it. Re-running is safe (skips anything already added).
- **Oversized grabs:** `fix_profiles.py` (disable Remux/2160p) +
  `cap_sizes.py` (lean size targets) + `cleanup_remux.py` (purge & re-grab).
- Some titles break text search (e.g. `WALL-E` → matches junk); add those by
  TMDB id (`lookup?term=tmdb:<id>`). See `OVERRIDES` in `add_boxoffice.py`.

See [`arr-tools/README.md`](arr-tools/README.md) for the full script reference.

## Conventions
- Secrets never get committed: `.env`, `*.conf`, `**/secrets/`, `**/credentials/`
  are gitignored. Use `*.example` / `*.template` files for shareable templates.
