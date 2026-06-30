#!/usr/bin/env python3
from arrlib import RADARR_URL, RADARR_KEY, SONARR_URL, SONARR_KEY
import json, urllib.request, urllib.error

APPS=[
 ("RADARR",RADARR_URL,RADARR_KEY),
 ("SONARR",SONARR_URL,SONARR_KEY),
]
# disable any quality whose name matches these (case-insensitive)
BAN=["remux","2160p","br-disk","raw-hd"]

def api(base,key,path,method="GET",body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(base+path,data=data,
        headers={"X-Api-Key":key,"Content-Type":"application/json"},method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        t=r.read().decode(); return json.loads(t) if t else None

def banned(name):
    n=(name or "").lower(); return any(b in n for b in BAN)

for app,base,key in APPS:
    p=api(base,key,"/api/v3/qualityprofile/6")
    changed=[]
    bluray1080_id=None
    for it in p["items"]:
        if it.get("items"):
            for sub in it["items"]:
                q=sub["quality"]
                if q["name"].lower()=="bluray-1080p": bluray1080_id=q["id"]
                if sub["allowed"] and banned(q["name"]):
                    sub["allowed"]=False; changed.append(q["name"])
            # group allowed if any child allowed
            it["allowed"]=any(s["allowed"] for s in it["items"])
            if it.get("name") and banned(it["name"]) and it["allowed"]:
                it["allowed"]=False
        else:
            q=it["quality"]
            if q["name"].lower()=="bluray-1080p": bluray1080_id=q["id"]
            if it["allowed"] and banned(q["name"]):
                it["allowed"]=False; changed.append(q["name"])
    # make sure cutoff is an allowed quality; prefer Bluray-1080p
    def is_allowed(qid):
        for it in p["items"]:
            if it.get("items"):
                for s in it["items"]:
                    if s["quality"]["id"]==qid: return s["allowed"]
            elif it["quality"]["id"]==qid: return it["allowed"]
        return False
    if not is_allowed(p["cutoff"]) and bluray1080_id:
        p["cutoff"]=bluray1080_id; changed.append(f"cutoff->Bluray-1080p({bluray1080_id})")
    api(base,key,"/api/v3/qualityprofile/6",method="PUT",body=p)
    print(f"{app}: disabled -> {', '.join(changed) if changed else '(nothing already)'}  | cutoff id={p['cutoff']}")
