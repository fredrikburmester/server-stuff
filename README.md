# server-stuff

Scripts and configs for self-hosted services.

## Ente Photos

End-to-end encrypted photo backup with disaster recovery to Backblaze B2.

### Scripts

| Script | Purpose |
|--------|---------|
| `backup-ente` | Daily backup - config tar + MinIO sync to B2 |
| `validate-backup` | Verify backup integrity (tar, SQL, MinIO sync) |
| `disaster-recovery` | Full bootstrap on fresh server from B2 |
| `ente-full-restore` | Restore on existing Ente setup |
| `setup-buckets` | One-time B2 bucket setup with versioning |

### Backup Strategy

- **Config tar** → `ente-backups:ente-photos-tar-backup`
  - docker-compose.yml, museum.yaml, postgres dump
- **MinIO data** → `ente-backups:ente-minio` (incremental sync)
  - Encrypted photo blobs

### Disaster Recovery

Spin up a complete Ente replica on any server:

```bash
# On fresh Ubuntu server
apt install docker.io docker-compose-v2 rclone

# Copy scripts
scp -r ente/ user@server:/opt/

# Run disaster recovery
cd /opt/ente
./disaster-recovery --rclone-conf=./rclone.conf \
  --appdata=/data/ente/config \
  --minio=/data/ente/minio
```

### Requirements

- Docker & Docker Compose
- rclone with B2 credentials
- Disk space: ~1.5x your photo library size

### B2 Buckets

| Bucket | Contents |
|--------|----------|
| `ente-photos-tar-backup` | Config snapshots (timestamped) |
| `ente-minio` | Encrypted photos (versioned) |
