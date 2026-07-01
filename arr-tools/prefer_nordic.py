#!/usr/bin/env python3
"""Prefer Nordic/Swedish releases in Radarr + Sonarr.

Creates two Custom Formats and gives them a positive score on the Any HD
profile (id 6), so Swedish/Nordic releases are *preferred* (win when available)
without blocking English/other grabs when no Nordic release exists.

  1. "Language: Swedish"          -> matches releases flagged Swedish audio
  2. "Nordic/Swedish (title)"     -> matches scene naming the flag misses
                                     (.NORDiC. / .SWEDiSH. / SweSub / SVE)

Idempotent: re-running reuses existing formats and just re-asserts the scores.
Run from inside arr-tools/ so `import arrlib` resolves.
"""
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY, api

APPS = [
    ("RADARR", RADARR_URL, RADARR_KEY),
    ("SONARR", SONARR_URL, SONARR_KEY),
]

PROFILE_ID = 6      # Any HD
SCORE = 50          # positive => preferred, not required

# Scene naming that the language flag frequently misses. Word-boundaried so we
# don't match e.g. "Sweden" in a title. SVE/SweSub cover Swedish subs/dubs.
TITLE_REGEX = r"\b(NORDiC|SWE(DiSH|SUB)?|SweSub|SVE|MULTi)\b"


def swedish_language_id(base, key):
    """Resolve Swedish languageId from the live API (don't hardcode)."""
    for lang in api(base, key, "/api/v3/language"):
        if lang.get("name", "").lower() == "swedish":
            return lang["id"]
    return None


def ensure_format(base, key, name, spec):
    """Create custom format `name` if absent; return its id either way."""
    for cf in api(base, key, "/api/v3/customformat"):
        if cf["name"] == name:
            return cf["id"], False
    body = {
        "name": name,
        "includeCustomFormatWhenRenaming": False,
        "specifications": [spec],
    }
    created = api(base, key, "/api/v3/customformat", method="POST", body=body)
    return created["id"], True


for app, base, key in APPS:
    swe_id = swedish_language_id(base, key)

    formats = []
    # Release-title regex (works even when the indexer sets no language flag).
    formats.append(ensure_format(base, key, "Nordic/Swedish (title)", {
        "name": "Nordic/Swedish keywords",
        "implementation": "ReleaseTitleSpecification",
        "negate": False,
        "required": False,
        "fields": [{"name": "value", "value": TITLE_REGEX}],
    }))
    # Language flag (only if we could resolve the id).
    if swe_id is not None:
        formats.append(ensure_format(base, key, "Language: Swedish", {
            "name": "Swedish",
            "implementation": "LanguageSpecification",
            "negate": False,
            "required": False,
            "fields": [{"name": "value", "value": swe_id}],
        }))

    want = {fid for fid, _ in formats}

    # Re-fetch the profile now that the formats exist, then set scores.
    prof = api(base, key, f"/api/v3/qualityprofile/{PROFILE_ID}")
    for item in prof["formatItems"]:
        if item["format"] in want:
            item["score"] = SCORE
    api(base, key, f"/api/v3/qualityprofile/{PROFILE_ID}", method="PUT", body=prof)

    made = [f"created id={fid}" if new else f"exists id={fid}" for fid, new in formats]
    swe = swe_id if swe_id is not None else "NOT FOUND (title regex only)"
    print(f"{app}: Swedish langId={swe} | scored +{SCORE} on profile {PROFILE_ID} -> {', '.join(made)}")
