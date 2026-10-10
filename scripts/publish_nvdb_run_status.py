#!/usr/bin/env python3
"""Publish latest NVDB Actions run metadata to a small public JSON file.
Only workflow metadata are stored; no secrets, tokens or Lastkajen data.
"""
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

repository=os.environ["GH_REPO"]
token=os.environ["GH_TOKEN"]
run_id=os.environ["RUN_ID"]
path="docs/data/nvdb-run-status.json"
url=f"https://api.github.com/repos/{repository}/contents/{path}"
headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
         "X-GitHub-Api-Version":"2022-11-28"}
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise
current=get(url)
status={
    "workflow":"Analyze NVDB traffic attributes",
    "run_id":int(run_id),
    "run_url":f"https://github.com/{repository}/actions/runs/{run_id}",
    "attempt":int(os.environ["RUN_ATTEMPT"]),
    "status":os.environ["RUN_STATUS"],
    "commit":os.environ["RUN_SHA"],
    "updated_utc":datetime.now(timezone.utc).isoformat(),
}
# Older run finishing after a newer one must not overwrite the latest run pointer.
if current:
    old=json.loads(base64.b64decode(current["content"]))
    if old.get("run_id",0)>status["run_id"]:
        print("Skipping stale run status update")
        raise SystemExit(0)
payload={"message":f"Record NVDB attribute run {run_id}: {status['status']}",
         "content":base64.b64encode((json.dumps(status,ensure_ascii=False,indent=2)+"\n").encode()).decode()}
if current:payload["sha"]=current["sha"]
request=urllib.request.Request(url,data=json.dumps(payload).encode(),
    headers={**headers,"Content-Type":"application/json"},method="PUT")
with urllib.request.urlopen(request,timeout=30) as response:
    print("Published NVDB run status",response.status)
