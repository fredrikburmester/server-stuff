# Media automation stack

Self-hosted movie/TV automation running on the **Unraid** box at
`192.168.1.105`. Everything is **LAN-only** — reachable at `192.168.1.105:<port>`
on the home network; there is no external/remote access.

> **Credentials** (API keys) are **not** in this file. They live in the
> gitignored `secrets/services.md` (and Radarr/Sonarr keys in `arr-tools/.env`).
> This doc is safe to commit.

## At a glance

| Service     | Role                         | URL                          | Port | Notes |
|-------------|------------------------------|------------------------------|------|-------|
| seerr       | Request frontend             | http://192.168.1.105:5055    | 5055 | Users request titles → Radarr/Sonarr |
| requestrr   | Discord request bot          | http://192.168.1.105:4545    | 4545 | Chat-based requests → seerr/*arr |
| Prowlarr    | Indexer manager              | http://192.168.1.105:9696    | 9696 | Syncs indexers → Radarr & Sonarr |
| Radarr      | Movie automation             | http://192.168.1.105:7878    | 7878 | Root `/movies` |
| Sonarr      | TV automation                | http://192.168.1.105:8989    | 8989 | Root `/tv` |
| SABnzbd     | Usenet downloader            | http://192.168.1.105:8082    | 8082 | **Primary** download path |
| qBittorrent | Torrent downloader           | http://192.168.1.105:8080    | 8080 | **Behind VPN (PIA)**; fallback path |
| Bazarr      | Subtitles                    | http://192.168.1.105:6767    | 6767 | Pulls from Radarr/Sonarr |
| Jellyfin    | Playback / library server    | http://192.168.1.105:8096    | 8096 | Serves `/movies` + `/tv` |

> **Removed:** `jackettvpn` was a second indexer proxy — fully superseded by
> Prowlarr (every Radarr/Sonarr indexer is Prowlarr-synced, none referenced
> Jackett). Container deleted; appdata left at `/mnt/user/appdata/jackett*`.
>
> **Software versions (verified):** Prowlarr 2.4.0 · Radarr 6.2.1 · Sonarr 4.0.19 ·
> SABnzbd 5.0.4 · qBittorrent 5.2.2 · Jellyfin 10.11.10 · seerr 3.2.0.

## How it flows

```
   requests:  seerr :5055  ·  requestrr :4545 (Discord)
                     │  approved requests
                     ▼
                 ┌──────────┐   syncs indexers    ┌─────────┐  ┌─────────┐
                 │ Prowlarr │────────────────────▶│ Radarr  │  │ Sonarr  │
                 │  :9696   │                     │  :7878  │  │  :8989  │
                 └──────────┘                     └────┬────┘  └────┬────┘
   indexers: NZBgeek (usenet, private)                 │            │
             EZTV/TPB/YTS/LimeTorrents/Nyaa (torrent)  │ send NZB/torrent
                                                        ▼            ▼
                              usenet ─▶ ┌─────────┐   torrent ─▶ ┌────────────┐
                                        │ SABnzbd │              │ qBittorrent│
                                        │  :8082  │              │   :8080    │
                                        └────┬────┘              │  (via VPN) │
                                             │                   └─────┬──────┘
                     completed downloads     │                         │
                     /downloads/completed/ ◀─┴─────────────────────────┘
                                             │  import (move to library)
                                             ▼
                            /movies  &  /tv  (unassigned drives)
                                             │
                                    ┌────────┴────────┐   subtitles   ┌────────┐
                                    │    Jellyfin     │◀──────────────│ Bazarr │
                                    │      :8096      │               │  :6767 │
                                    └─────────────────┘               └────────┘
```

1. **Prowlarr** holds all indexer definitions and pushes them to Radarr & Sonarr
   (fullSync) — you add/remove an indexer once, in Prowlarr.
2. You add a movie/show in **Radarr/Sonarr** (usually via the `arr-tools/`
   scripts). It searches the synced indexers.
3. Results are handed to a **download client** by protocol:
   - **Usenet → SABnzbd** (preferred, no delay)
   - **Torrent → qBittorrent** (only after a 30-min delay — usenet gets first shot)
4. Completed downloads land in `/downloads/completed/`; Radarr/Sonarr import them
   (move) into `/movies` and `/tv`.
5. **Bazarr** fetches subtitles for the imported files; **Jellyfin** serves the
   libraries for playback.

## Services in detail

### seerr — request frontend (`:5055`)
The user-facing "Netflix-style" request UI (a **Jellyseerr/Overseerr** fork).
People browse and request movies/shows; approved requests are handed to Radarr
(movies) and Sonarr (TV), which then acquire them through the pipeline below.
Also syncs the Jellyfin library so it knows what's already available.

### requestrr — Discord request bot (`:4545`)
A Discord chatbot for requesting titles from chat. Wired to seerr/*arr so
requests made in Discord flow into the same acquisition pipeline. Optional
convenience layer on top of seerr.

### Prowlarr — indexer manager (`:9696`)
Single source of truth for indexers. Synced apps: **Radarr** and **Sonarr**
(both `fullSync`). Lidarr is registered but sync is **disabled** (no music setup).

Current indexers:

| Indexer        | Protocol | Privacy      | Enabled |
|----------------|----------|--------------|---------|
| NZBgeek        | usenet   | private      | ✅ (1-yr sub) |
| EZTV           | torrent  | public       | ✅ |
| The Pirate Bay | torrent  | public       | ✅ |
| YTS            | torrent  | public       | ✅ |
| LimeTorrents   | torrent  | public       | ✅ |
| Nyaa.si        | torrent  | public       | ✅ |
| RuTracker.org  | torrent  | semi-private | ❌ (disabled) |

### Radarr — movies (`:7878`)
- Root folder: `/movies` (an Unraid unassigned drive)
- Quality profile: **Any HD** (id 6) — Remux/2160p/BR-DISK/Raw-HD disabled
- Size caps via `arr-tools/cap_sizes.py`: preferred ≈ 45 MB/min, max ≈ 70 MB/min
  (~5.2 GB / ~8 GB for a ~115-min film; scales with runtime)
- Download clients: SABnzbd (cat `movies`) + qBittorrent (cat `radarr`)

### Sonarr — TV (`:8989`)
- Root folder: `/tv` (an Unraid unassigned drive)
- Quality profile: **Any HD** (id 6)
- Download clients: SABnzbd (cat `tv`) + qBittorrent (cat `tv-sonarr`)
- "Monitor new items" tips: to follow only *future* episodes of an ended/ongoing
  show, unmonitor aired episodes and leave the series `monitorNewItems=all`.

### SABnzbd — usenet downloader (`:8082`)  ← primary
- Provider: **Frugal Usenet** — connections capped at **20** (mitigates
  "502 Access denied to your node" throttling).
- Block account: **Blocknews** *pending* — redeem code (~Jul 2026) then add as a
  low-priority backup server for completion on a different backbone.
- Categories map to library folders: `movies` → `/movies`, `tv` → `/tv`.
- Completed downloads go to `/downloads/completed/` (see path mapping below).

### qBittorrent — torrent downloader (`:8080`)  ← behind VPN
- Container: **`binhex-qbittorrentvpn`** (appdata: `/mnt/user/appdata/binhex-qbittorrentvpn`).
- VPN: **PIA over OpenVPN** — endpoint `sweden.privacy.network:1197/udp`
  (config `openvpn/sweden.ovpn`; PIA login in `openvpn/credentials.conf`).
  `LAN_NETWORK=192.168.1.0/24` keeps the WebUI reachable while all torrent
  traffic is tunneled; kill-switch means qBit stops if the tunnel drops.
- Fallback only: Radarr/Sonarr prefer usenet and apply a **30-min torrent delay**,
  so torrents are grabbed only if usenet hasn't satisfied the release.
- Categories: `radarr` (movies), `tv-sonarr` (TV).

### Bazarr — subtitles (`:6767`)
Connects to Radarr & Sonarr (via their API keys) and downloads subtitles for
imported media. Languages configured: English + Swedish.

### Jellyfin — playback (`:8096`)
Serves the `/movies` and `/tv` libraries. Radarr/Sonarr send an on-import
notification so new content shows up without waiting for a full scan.

## Download client config (shared)

Both Radarr and Sonarr point at the **same two clients** on `192.168.1.105`:

| Client      | Port | Radarr cat | Sonarr cat | Protocol | Priority |
|-------------|------|------------|------------|----------|----------|
| SABnzbd     | 8082 | `movies`   | `tv`       | usenet   | preferred (0-min delay) |
| qBittorrent | 8080 | `radarr`   | `tv-sonarr`| torrent  | fallback (30-min delay) |

**Remote path mapping** (both apps): host `192.168.1.105`,
`/downloads/` → `/downloads/completed/` — because SAB reports paths under
`/downloads/` while the *arr containers see the completed subfolder.

## Storage & paths (Unraid)

- **Downloads (cache disk):** `/mnt/user/Downloads` with `complete`/`incomplete`
  subfolders. Fast landing zone; files are then moved out to the media drives.
- **Movies:** unassigned drive `6160A04UFATG` → exposed to containers as `/movies`
- **TV:** unassigned drive `ZTN12DVP` → exposed as `/tv`
- Media lives on **unassigned drives, not the array** — no parity/redundancy
  (acceptable for re-downloadable media; spreads movies vs TV across two disks).
- No hardlinks needed on the usenet path (nothing seeds), so import = move.

## Operating notes

- **Adding media:** use the scripts in [`arr-tools/`](../arr-tools/) — never
  hand-roll API calls. See its README.
- **Removing media:** deleting a series/movie in Radarr/Sonarr does **not** cancel
  in-flight downloads in SAB/qBittorrent. Clear **both sides** — remove from the
  *arr, then delete the queue item + files in the download client.
- **Oversized grabs:** `arr-tools/fix_profiles.py` + `cap_sizes.py` +
  `cleanup_remux.py`.
- **Migration context:** this stack replaced a Real-Debrid setup; the
  `real-debrid/` folder is legacy (see repo `CLAUDE.md`).

## Credentials

Not stored here. See gitignored:
- `secrets/services.md` — all URLs/ports + API keys (Prowlarr, SAB, Jellyfin, qBit)
- `arr-tools/.env` — Radarr/Sonarr URLs + API keys (permission-locked)
