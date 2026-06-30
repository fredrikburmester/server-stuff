"""Shared config + helpers for the Radarr/Sonarr tools.

Credentials are loaded from a local `.env` file (gitignored) so they never get
committed. Copy `.env.example` to `.env` and fill in your API keys.
"""
import json, os, urllib.request, urllib.error


def _load_env():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

RADARR_URL = os.environ.get("RADARR_URL", "http://192.168.1.105:7878").rstrip("/")
RADARR_KEY = os.environ.get("RADARR_KEY", "")
SONARR_URL = os.environ.get("SONARR_URL", "http://192.168.1.105:8989").rstrip("/")
SONARR_KEY = os.environ.get("SONARR_KEY", "")


def api(base, key, path, method="GET", body=None, timeout=60):
    """Minimal *arr v3 API helper. Returns parsed JSON (or None for empty body)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path, data=data,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        t = r.read().decode()
        return json.loads(t) if t else None
