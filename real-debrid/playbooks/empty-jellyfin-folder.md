# Playbook — "Empty folder in Jellyfin, but Sonarr/Radarr says it's there"

Diagnose & fix the case where:
- Sonarr/Radarr shows the item as available (`hasFile: true`, full episode counts).
- The files exist on the host as symlinks into `/mnt/remotes/realdebrid/__all__/…`.
- Jellyfin renders an **empty folder** for the series (or the movie is missing entirely).

Companion to `../decypharr-jellyfin-runbook.md` (full incident writeup). This is the
short, reusable diagnostic path. Host: `ssh root@192.168.1.105`.

---

## TL;DR — the two failure modes

| Mode | What you see | Root cause | Fix |
|---|---|---|---|
| **A. Orphaned items** | Folder empty; flat search finds episode items with `SeriesId/SeasonId/IndexNumber = null` | Jellyfin scanned the folder while RD/FUSE reads were failing → it created episode rows it couldn't probe → orphaned from series hierarchy | Move symlinks aside → `DELETE` orphan items → move symlinks back → series recursive refresh in a quiet pipeline |
| **B. Dangling symlink** | File "exists" in arr DB; on host the symlink is `l????????? ?` (kernel can't stat); decypharr `__bad__` knows about it | RD torrent DMCA'd or dead; symlink points to a torrent decypharr has marked bad | Delete dangling symlink → `DELETE /api/v3/moviefile/{id}` (or `/episodefile/`) → trigger search to re-grab |

Most "empty folder" reports are A. The orphaning is triggered by the recurrence driver
below — fix the driver and you stop creating new orphans.

---

## The recurrence driver (fix this first if you haven't)

If you keep seeing new orphans:

```bash
ssh root@192.168.1.105 'curl -s "http://localhost:8096/Library/VirtualFolders?api_key=$JFK" \
  | jq -r ".[] | \"\(.Name): realtime=\(.LibraryOptions.EnableRealtimeMonitor)\""'
```

For any **RD-backed library** (`Movies`, `4K Movies`, `TV-Shows`), `realtime=true` is the
recurrence engine: a churning FUSE mount fires FS events constantly → Jellyfin re-refreshes
the whole library every ~10 min → each pass re-probes a standing pile of ~hundreds of
DMCA'd/dead torrents → `Input/output error` storm → fresh orphans on whatever was
imported during the window. Disable it (sets each library's `EnableRealtimeMonitor=false`
while preserving other options):

```bash
ssh root@192.168.1.105 bash -s <<'REMOTE'
JFK=$(sqlite3 /mnt/user/appdata/sonarr-v1/sonarr.db \
  "SELECT Settings FROM Notifications WHERE Implementation='MediaBrowser';" | jq -r '.apiKey')
curl -s "http://localhost:8096/Library/VirtualFolders?api_key=$JFK" \
  | jq -c '.[] | select(.Name|test("Movies|TV-Shows";"i")) | {Id: .ItemId, name: .Name}' \
  | while read row; do
      ID=$(echo "$row" | jq -r '.Id'); NAME=$(echo "$row" | jq -r '.name')
      OPTS=$(curl -s "http://localhost:8096/Library/VirtualFolders?api_key=$JFK" \
        | jq -c --arg id "$ID" '.[] | select(.ItemId==$id) | .LibraryOptions | .EnableRealtimeMonitor=false')
      BODY=$(jq -nc --arg id "$ID" --argjson o "$OPTS" '{Id:$id, LibraryOptions:$o}')
      curl -s -o /dev/null -w "$NAME: %{http_code}\n" -X POST \
        "http://localhost:8096/Library/VirtualFolders/LibraryOptions?api_key=$JFK" \
        -H "Content-Type: application/json" -d "$BODY"
    done
REMOTE
```

Replacement for realtime: Sonarr/Radarr Connect (`MediaBrowser`) notification already fires
`onDownload + onImportComplete` with `updateLibrary=true` — that triggers a **targeted**
path scan on real imports, not a full sweep.

Effect when this lands: iowait / load drop within seconds; `Input/output error` count in
`docker logs jellyfin` goes to 0. That's the confirmation.

---

## Mode A — Orphaned items (the usual "empty folder")

### 1. Triage (read-only, ~30s)

```bash
ssh root@192.168.1.105 bash -s <<'REMOTE'
TITLE="Off Campus"      # ← edit
LIB=tv-shows            # tv-shows | movies
JFK=$(sqlite3 /mnt/user/appdata/sonarr-v1/sonarr.db \
  "SELECT Settings FROM Notifications WHERE Implementation='MediaBrowser';" | jq -r '.apiKey')

echo "--- 1. files on host (must show symlinks pointing into /mnt/remotes/realdebrid) ---"
find "/mnt/cache/RDDATA/media/$LIB" -path "*$TITLE*" -printf '%y\t%l\t%p\n' 2>/dev/null

echo "--- 2. read-test (proves files are healthy NOW) ---"
F=$(find "/mnt/cache/RDDATA/media/$LIB" -path "*$TITLE*" -type l \( -iname '*.mkv' -o -iname '*.mp4' \) | head -1)
docker exec jellyfin /usr/lib/jellyfin-ffmpeg/ffprobe -v error \
  -show_entries format=duration -of csv=p=0 "${F/\/mnt\/cache\/RDDATA/\/mnt}" 2>&1; echo "exit=$?"

echo "--- 3. Jellyfin's view of the series + its children ---"
SID=$(curl -s "http://localhost:8096/Items?searchTerm=$(printf %s "$TITLE" | jq -sRr @uri)&Recursive=true&IncludeItemTypes=Series&api_key=$JFK" \
  | jq -r '.Items[0].Id // empty')
echo "series id: $SID"
echo "children under series: $(curl -s "http://localhost:8096/Items?parentId=$SID&Recursive=true&IncludeItemTypes=Episode&api_key=$JFK" | jq -r '.TotalRecordCount')"

echo "--- 4. flat-search for episode items by name (the smoking gun) ---"
curl -s "http://localhost:8096/Items?searchTerm=$(printf %s "$TITLE" | jq -sRr @uri)&Recursive=true&IncludeItemTypes=Episode&fields=Path&api_key=$JFK" \
  | jq -r '.Items[]? | "\(.Name) | idx=\(.IndexNumber) sid=\(.SeriesId) parent=\(.ParentId)"'
REMOTE
```

**Diagnose by the output:**

| Triage output | Diagnosis |
|---|---|
| Step 1 shows `l????????? ?` for the symlinks | Mode B (dangling symlinks) — go to Mode B |
| Step 2 ffprobe exit ≠ 0 / hangs (timeout) | Files genuinely unreadable now → either FUSE wedge ([runbook §1](../decypharr-jellyfin-runbook.md#1-media-wouldnt-play--but-rddecypharr-were-fine)) or that file is DMCA'd → check decypharr `__bad__`/logs |
| Step 3 children=0 **and** Step 4 returns episodes with `idx/sid/parent = null` | **Confirmed Mode A — orphaned items.** Proceed below. |
| Step 3 children=0 **and** Step 4 returns nothing | Never ingested. Fire `/Items/{seriesId}/Refresh?recursive=true&replaceAllMetadata=false` (with `metadataRefreshMode=Default`) in a quiet pipeline. |

### 2. Fix — symlinks-aside method (files never at risk)

This is the safest repair: Jellyfin's `DELETE /Items/{id}` tries to remove the underlying
file. By moving the symlinks out of the folder first, the delete drops the DB row and
"deletes" a no-longer-present path. We then restore the symlinks and re-ingest cleanly.

```bash
ssh root@192.168.1.105 bash -s <<'REMOTE'
set -e
TITLE="Off Campus"      # ← edit
LIB=tv-shows            # tv-shows | movies
JFK=$(sqlite3 /mnt/user/appdata/sonarr-v1/sonarr.db \
  "SELECT Settings FROM Notifications WHERE Implementation='MediaBrowser';" | jq -r '.apiKey')
SRC="/mnt/cache/RDDATA/media/$LIB/$TITLE"
TMP="/mnt/cache/RDDATA/.jellyfix_$(echo "$TITLE" | tr -dc A-Za-z0-9)"

# 1. stash symlinks (mkv + mp4 only; leave .srt / .nfo)
mkdir -p "$TMP"
mv "$SRC"/*.mkv "$SRC"/*.mp4 "$TMP"/ 2>/dev/null || true
echo "stashed: $(ls -1 "$TMP" | wc -l) symlinks; folder now: $(ls -1 "$SRC" | wc -l) files"

# 2. DELETE orphan items by API
for ID in $(curl -s "http://localhost:8096/Items?searchTerm=$(printf %s "$TITLE" | jq -sRr @uri)&Recursive=true&IncludeItemTypes=Episode,Movie&api_key=$JFK" | jq -r '.Items[].Id'); do
  curl -s -X DELETE "http://localhost:8096/Items/$ID?api_key=$JFK" -w "  $ID -> HTTP %{http_code}\n"
done

# 3. restore symlinks
mv "$TMP"/* "$SRC"/ 2>/dev/null || true; rmdir "$TMP" 2>/dev/null || true
echo "restored: $(ls -1 "$SRC" | wc -l) files in folder"

# 4. wait for quiet pipeline, then refresh
for i in $(seq 1 6); do
  ERR=$(docker logs --since 90s jellyfin 2>&1 | grep -c "Input/output error")
  [ "$ERR" -eq 0 ] && break
  echo "waiting (IOerr last 90s=$ERR)..."; sleep 30
done
SID=$(curl -s "http://localhost:8096/Items?searchTerm=$(printf %s "$TITLE" | jq -sRr @uri)&Recursive=true&IncludeItemTypes=Series&api_key=$JFK" | jq -r '.Items[0].Id // empty')
[ -n "$SID" ] && curl -s -X POST "http://localhost:8096/Items/$SID/Refresh?metadataRefreshMode=Default&imageRefreshMode=Default&replaceAllMetadata=false&recursive=true&api_key=$JFK" -w "refresh HTTP %{http_code}\n"
REMOTE
```

### 3. Verify

```bash
ssh root@192.168.1.105 bash -s <<'REMOTE'
TITLE="Off Campus"
JFK=$(sqlite3 /mnt/user/appdata/sonarr-v1/sonarr.db "SELECT Settings FROM Notifications WHERE Implementation='MediaBrowser';" | jq -r '.apiKey')
SID=$(curl -s "http://localhost:8096/Items?searchTerm=$(printf %s "$TITLE" | jq -sRr @uri)&Recursive=true&IncludeItemTypes=Series&api_key=$JFK" | jq -r '.Items[0].Id // empty')
curl -s "http://localhost:8096/Items?parentId=$SID&Recursive=true&IncludeItemTypes=Episode&api_key=$JFK" \
  | jq -r '.Items[]? | "  S\(.ParentIndexNumber // "?")E\(.IndexNumber // "?"): \(.Name)"'
REMOTE
```

You want each episode showing `S1E1:`, `S1E2:`, … — not `S?E?:`. If it lands as
"Season Unknown", run a `metadataRefreshMode=FullRefresh&replaceAllMetadata=true` on
the series item; the TVDB/TMDB match will fix the season grouping.

**Gotcha:** `/Library/Media/Updated` (the targeted-path-scan endpoint) accepts HTTP 204
and only refreshes existing items — it will **not** discover children of an empty series
shell. For discovery, use `/Items/{seriesId}/Refresh?recursive=true`.

---

## Mode B — Dangling symlink (RD torrent dead)

Symptom: `ls -la "<folder>"` shows `l????????? ?` for the file. `ffprobe` errors with
`Input/output error`. `decypharr` logs `marked as bad` / `still resolves to an empty link
after 3 re-insertion attempts` for that filename.

### Fix — re-grab via arr

The naive `DELETE /api/v3/moviefile/{id}` **will hang** because Radarr tries to delete the
underlying file and stat() on a dangling FUSE symlink stalls. Remove the symlink manually
first, then DELETE, then search.

```bash
ssh root@192.168.1.105 bash -s <<'REMOTE'
TMDB_TITLE="The Matrix"   # ← edit
YEAR=1999
RAK=$(grep -oE '[a-f0-9]{32}' /mnt/user/appdata/radarr/config.xml | head -1)
B="http://localhost:7878/api/v3"

# 1. locate movie in Radarr
M=$(curl -s "$B/movie?apikey=$RAK" | jq -c --arg t "$TMDB_TITLE" --argjson y $YEAR \
  '.[] | select(.title==$t and .year==$y) | {id,path, mfid: .movieFile.id, rel: .movieFile.relativePath}')
echo "$M"
ID=$(echo "$M" | jq -r '.id'); MFID=$(echo "$M" | jq -r '.mfid'); P=$(echo "$M" | jq -r '.path'); REL=$(echo "$M" | jq -r '.rel')
FILE="$P/$REL"

# 2. remove the dangling symlink BEFORE calling DELETE
ls -la "$FILE" 2>&1 | head -1
rm -f "$FILE"

# 3. DELETE moviefile (now safe — no file to hang on)
curl -s --max-time 30 -X DELETE "$B/moviefile/$MFID?apikey=$RAK" -w "DELETE HTTP %{http_code}\n"

# 4. confirm + trigger search
curl -s "$B/movie/$ID?apikey=$RAK" | jq '{hasFile}'
curl -s -X POST "$B/command?apikey=$RAK" -H "Content-Type: application/json" \
  -d "{\"name\":\"MoviesSearch\",\"movieIds\":[$ID]}" | jq '{id,name,status}'
REMOTE
```

For series, swap to: `/api/v3/episodefile/{id}` on Sonarr (`port 8989`,
config at `/mnt/user/appdata/sonarr-v1/config.xml`) and `EpisodeSearch` command.

Watch for the new symlink to appear in the folder (usually 30s–5min). If multiple titles
are dead, batch via `DELETE /api/v3/moviefile/bulk` — but still `rm -f` each symlink first.

---

## How to **download** an item to your local Mac

These are debrid streams, not local files — but rsync over SSH will follow the symlink
through FUSE and pull the bytes down:

```bash
rsync -avh --progress \
  'root@192.168.1.105:/mnt/cache/RDDATA/media/movies/<Title>/' \
  ~/Downloads/<Title>/
```

(The trailing `/` on the source means "contents of folder" → grabs the .mkv/.mp4 plus
any .srt sidecar.) Run it from the Mac, not the server. If it hangs, the source torrent
is probably dead (Mode B).

---

## Why this keeps happening (one-screen mental model)

1. **Real-Debrid attrition is continuous.** Hundreds of torrents end up DMCA'd / dead at
   any given time. Decypharr knows (`__bad__` list), but symlinks created before the
   takedown stay in place, and arr DBs still believe `hasFile: true`.
2. **Anything that scans the whole library re-reads every file**, including the dead ones.
   Each dead read hangs ~30–45 s.
3. **Concurrent hung reads = the I/O storm.** Throughput collapses, healthy probes start
   failing too, and Jellyfin creates broken (orphaned) records for files imported during
   the storm.
4. **The thing that triggers the scan is the recurrence engine.** A scheduled full scan
   (runbook §8) was the original engine. Real-time monitoring (runbook §"Solutions
   applied" replacement) turned out to be the *next* engine, firing every ~10 min on
   FUSE-mount churn. Both are fundamentally hostile to a debrid library.
5. **Right shape:** scheduled full scan = OFF, real-time monitor = OFF on RD libraries,
   new content arrives only via arr → Jellyfin Connect (targeted single-path scan). Periodic
   `decypharr-cleanup` removes the dead pile so even if something *does* re-read it, there's
   less fuel.

---

## Reference links

- [Full incident runbook](../decypharr-jellyfin-runbook.md) — original May 2026 writeup.
- [Mount setup](../mount-real-debrid) — the FUSE layering this all sits on.
