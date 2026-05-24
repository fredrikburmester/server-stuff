# Jellyfin + Decypharr + Real-Debrid + Unraid — Incident Runbook

Full writeup of the May 2026 debugging session: media wouldn't play → cascading
FUSE/import/overload issues → root causes, fixes, and the permanent changes now
in place. Written as a reusable runbook.

Host: Unraid, `ssh root@192.168.1.105`.

---

## Stack architecture

```
Real-Debrid (cloud)
   ↑ HTTP/webdav (rate-limited 250/min)
decypharr  (container cy01/blackhole)  — qBittorrent-compatible download client for Sonarr/Radarr
   ├─ adds torrents to RD, exposes them via internal webdav (:8282/webdav)
   ├─ runs rclone (rcd :5572) which FUSE-mounts that webdav at /mnt/remotes/realdebrid (inside container)
   ├─ VFS cache on disk (vfs_cache_mode=full, ~50 GB) at /app/cache/vfs
   └─ creates download symlinks in /mnt/symlinks/<arr>/  → /mnt/remotes/realdebrid/__all__/<torrent>/<file>
Sonarr / Radarr
   ├─ use decypharr as their download client (qbit API on :8282)
   └─ import = hardlink decypharr's download symlink into /media/movies|tv-shows/ (becomes a symlink → /remotes/realdebrid)
Jellyfin
   └─ reads /media/... (symlinks resolving through FUSE → decypharr → RD)
Unraid host
   ├─ /mnt/user/* is shfs (a FUSE union over cache pool + array) — "user shares"
   ├─ /mnt/cache = NVMe cache pool (where RDDATA + appdata physically live)
   └─ Docker via Compose Manager (decypharr, radarr) and dockerman templates (jellyfin, sonarr-v3)
```

**Critical layering insight:** reads travel `Jellyfin → /media symlink → FUSE(rclone) → decypharr webdav → RD`.
When containers bind `/mnt/user/...`, there's an **extra shfs FUSE layer** in front of everything — FUSE-over-FUSE.

---

## The incidents (in causal order)

### 1. Media wouldn't play — but RD/decypharr were fine
- **Symptom:** Jellyfin playback hung; "Input/output error" / "ffprobe failed - streams and format are both null".
- **Investigation:** RD account healthy. Direct webdav GET fast (7–9 MB/s). Direct cache-file read 923 MB/s.
  But reads through the **FUSE mount hung 30s → "context canceled"** for *every* file.
- **Root cause:** rclone VFS **wedged** — `vfs/stats` showed `inUse: 5` with no transfers + **718** accumulated
  `timeout awaiting response headers`. Killed-mid-read clients (ffprobe/dd) left stuck handles → rclone
  connection pool exhausted → every new read timed out.
- **Fix:** `docker restart decypharr` cleared in-memory rclone state. Reads back to 118 MB/s, errors → 0.

### 2. Bad-torrent accumulation (steady-state attrition)
- **Symptom:** specific titles wouldn't play (24, later 677 entries).
- **Root cause:** ~10% of a large RD library rots — mostly **HTTP 451 (DMCA takedowns)**, some 404/202.
  decypharr marks them "bad" and refuses to serve.
- **Diagnosis:** `GET /api/browse/__bad__` (paginated, **API caps at 50/page** regardless of `limit`).
  decypharr log: `realdebrid API error: Status: 451` then `can't repair ... marked as bad`.
- **Fix:** bulk `DELETE /api/browse/torrents/{hash}` for every bad entry.

### 3. Ghost files (Radarr/Sonarr DB out of sync with RD)
- **Symptom:** e.g. "Star Wars: The Force Awakens", "Your Name" visible in Jellyfin but failed: "Could not find file".
- **Root cause:** RD torrent removed (DMCA/cleanup), but the **symlink in /media and the Radarr `MovieFile`
  record persisted**. `MissingMoviesSearch` ignored them because Radarr still thought `hasFile: true`.
- **Fix:** `DELETE /api/v3/moviefile/{id}` (flips `hasFile→false`) → targeted search.
  Orphans not in Radarr at all → re-added via `POST /api/v3/movie` with `tmdbId` + `searchForMovie`.

### 4. Mass cleanup (full audit)
- **Found:** 6,630 → later 4,850 broken symlinks; 677 bad torrents.
- **Method:** dump decypharr `__all__` (good) + `__bad__`, extract all `/media` symlink targets via
  `find -printf '%l\t%p\n'`, cross-check target torrent-folders against decypharr's library.
  Symlinks pointing to bad-or-missing folders = broken.
- **Fix sequence:** delete bad torrents → delete broken symlinks → bulk `DELETE /api/v3/moviefile/bulk`
  + `/api/v3/episodefile/bulk` → clean empty dirs.

### 5. FUSE-over-shfs (the structural root cause)
- **Found:** decypharr bound `/mnt/user/appdata/decypharr:/app` and `/mnt/user/RDDATA:/mnt` — both through
  **shfs**. Every VFS-cache read = FUSE(rclone)→docker→FUSE(shfs)→cache. Triple-FUSE on the hot path →
  source of "Socket not connected"/"Transport endpoint is not connected" wedges
  (known rclone behavior: https://github.com/rclone/rclone/issues/7766).
- **Fix:** changed compose binds to `/mnt/cache/RDDATA` + `/mnt/cache/appdata/decypharr` (direct cache pool,
  bypassing shfs). Safe because RDDATA is `cache=only` and appdata mover is `Array→Cache`.

### 6. Mount propagation / zombie FUSE mounts
- **Symptom:** after decypharr recreate, consumers got "Transport endpoint is not connected".
- **Root cause:** old container's FUSE mount, propagated to host, **wasn't cleanly unmounted** on teardown →
  kernel kept a dead mount entry. Consumers' bind snapshots went stale.
- **Fix:** `fusermount -u <stale mount>` to clear the zombie; restart consumer containers to re-attach.

### 7. Unkillable zombie container (after a manual stop / Jellyfin update)
- **Symptom:** `docker stop`/`restart` → "tried to kill container, but did not receive an exit event".
  Container "Up" but app dead; `docker exec` → OCI setns error.
- **Root cause:** ffprobe children stuck in **D-state on FUSE reads** → s6-svscan (container PID 1) couldn't
  reap them. PID-1-of-namespace **ignores SIGKILL** unless forcibly delivered; `kill -9`, `docker kill`,
  `runc kill`, `cgroup.kill` all failed.
- **Fix path:** kill `containerd-shim` (Docker then sees it exited); stale runc/containerd task dirs blocked
  restart; ultimately a **Docker daemon restart** (`/etc/rc.d/rc.docker restart`) cleared everything.

### 8. The self-inflicted IO storm (load → 94)
- **Trigger:** after the bulk cleanup, fired global `MissingMoviesSearch` + `MissingEpisodeSearch` (thousands).
  Radarr/Sonarr grabbed en masse → decypharr (600 workers) hammered RD → 250/min limit throttled → reads
  queued → **Jellyfin's simultaneous automatic library scan** ffprobed every file over the throttled FUSE mount.
- **Symptom:** load 94, iowait 80%, 20 blocked D-state procs, threads 4,700→6,900; `ps`/`pgrep` themselves
  hung (D-state reading stuck `/proc`). Memory fine — pure IO saturation.
- **Diagnosis tools that worked when `ps` hung:** `/proc/loadavg`, `vmstat` (`b`=blocked, `wa`=iowait),
  reading `/proc/$pid/stat` field 3 + `/proc/$pid/wchan` directly, mapping `/proc/$pid/cgroup` → container.
- **Smoking gun:** Jellyfin log `Scan Media Library Cancelled after 1804 minute(s)` — a **30-hour** scan,
  structurally guaranteed to wedge on an RD/FUSE library.
- **Fix:** `docker restart decypharr` aborted all in-flight FUSE reads → stuck ffprobe died → threads halved,
  load collapsed 94→3. Then stopped Jellyfin (cleanly, once children gone), restarted Sonarr/Radarr.

### 9. Stalled imports (38 movies stuck)
- **Symptom:** movies grabbed during the storm sat at `importPending`/`importBlocked`; `hasFile` stayed false.
- **Root causes (layered):**
  - decypharr restart interrupted symlink creation for some.
  - Radarr **"downloadIgnored" / "matched to movie by ID, manual import required"** — release names didn't parse.
  - Forcing manual import still failed: Radarr's import runs **ffprobe for sample-detection**
    (NOT disabled by `enableMediaInfo=false`), and it got **`Input/output error`** because the re-grabbed
    releases weren't reliably served by the throttled RD.
- **Resolution:** updating decypharr (2.2→2.3, "fixes for DFS hangs with queueing for all imports") + lowering
  workers let most drain on their own (13→3). Last 3 were bad releases →
  **blocklisted + removed** (`DELETE /api/v3/queue/{id}?removeFromClient=true&blocklist=true`) + targeted re-search.

---

## Root causes (short list)
1. **FUSE-over-shfs** on Unraid `/mnt/user` paths → fragile reads, frequent wedges.
2. **rclone doesn't cleanly unmount with ops in flight** → zombie mounts (known upstream).
3. **ffprobe-over-FUSE in D-state** can't be killed → cascades into unkillable containers.
4. **Jellyfin automatic full library scan** over RD/FUSE → 30-hour scans → IO storm.
5. **Global mass-searches** overwhelm RD's 250/min limit → thundering herd.
6. **decypharr 600 workers** amplified it; **2.2-stable** had import-queue hang bugs.
7. **RD attrition (~10%, mostly DMCA 451)** → continuous bad torrents + ghost files.
8. **restart policies** were `no` on jellyfin/sonarr-v3 → silent non-recovery.

---

## Solutions applied (permanent changes)
| Change | What |
|---|---|
| decypharr binds | `/mnt/user/...` → `/mnt/cache/...` (bypass shfs FUSE-over-FUSE) |
| decypharr version | 2.2-stable → **2.3-stable** (import-queue hang fixes) |
| decypharr workers | 600 → **100** (gentler on RD) |
| restart policy | jellyfin + sonarr-v3 → `always`; decypharr → `always` |
| Jellyfin scan | scheduled "Scan Media Library" **disabled**; real-time monitoring on |
| New-content detection | Radarr + Sonarr → Jellyfin **Connect** notifications (On Import/Upgrade/Rename) — targeted refresh, no full scan |
| Cleanup automation | User Script `decypharr-cleanup` (cleanup only, **no mass-search**), cron `0 5 1 * *` (monthly), guards (abort if <2000 good torrents, or >40% symlinks would delete); logs `/var/log/decypharr-cleanup.log` |
| Library state | 677 bad torrents + 4,850 dead symlinks removed, 15 orphans re-added, 3 bad releases blocklisted |

---

## Key reference (commands & endpoints)

**Diagnosing a FUSE wedge** (when `ps` hangs):
```bash
cat /proc/loadavg ; vmstat 1 2          # b=blocked, wa=iowait
# D-state procs + what they wait on:
for p in /proc/[0-9]*; do [ "$(cut -d' ' -f3 $p/stat)" = D ] && echo "$(cat $p/comm) $(cat $p/wchan)"; done
grep -oE 'docker[/-][0-9a-f]{12}' /proc/<pid>/cgroup   # which container
```

**Decypharr API:** `/api/browse/__all__`, `/api/browse/__bad__` (50/page cap),
`DELETE /api/browse/torrents/{hash}`, rclone RC `:5572/core/stats`, `:5572/vfs/stats`, `:5572/vfs/forget`.

**Clear a zombie FUSE mount:** `fusermount -u /mnt/cache/RDDATA/remotes/realdebrid`

**Unkillable container:** kill `containerd-shim`; clear `/var/run/docker/.../task/moby/<cid>`;
else `/etc/rc.d/rc.docker restart`.

**Radarr/Sonarr:** `DELETE /api/v3/{movie,episode}file/bulk`,
`DELETE /api/v3/queue/{id}?removeFromClient=&blocklist=`,
`POST /api/v3/command {MoviesSearch|ProcessMonitoredDownloads|RescanMovie}`.

---

## Gotchas worth remembering
- **`enableMediaInfo=false` does NOT stop import-time ffprobe** (sample detection still runs).
- **`docker stop` on a container with D-state FUSE children hangs** and can leave it unkillable.
- **Recreating decypharr breaks consumers' mount view** — restart them or they get "transport endpoint not connected".
- **decypharr `repair` only resubmits magnets** — useless for DMCA'd (451) content.
- **RescanMovie/Series fail with "Socket not connected"** when any in-scope file is FUSE-wedged — bulk
  file-record DELETE is more reliable.
- **Never fire global Missing*Search on a debrid library** — stagger it.
- Load average is inflated by D-state procs; check `vmstat` `wa`/`b` and free memory to distinguish IO-wait
  from real overload.
- decypharr browse API + RD `/torrents` both paginate; `limit` is capped — always loop pages.
- API keys (RD / Sonarr / Radarr) were exposed during debugging — rotate them.
