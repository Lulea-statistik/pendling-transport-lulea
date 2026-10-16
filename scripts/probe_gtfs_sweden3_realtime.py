#!/usr/bin/env python3
"""Bounded GTFS Sweden 3 RT feed availability audit; no raw positions stored."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
KEY=os.environ.get("GTFS_SWEDEN_3_REALTIME","").strip()
BASE="https://opendata.samtrafiken.se/gtfs-rt-sweden"
OPERATORS=("norrbotten","lulea","sl")
FEEDS=("TripUpdatesSweden.pb","VehiclePositionsSweden.pb","ServiceAlertsSweden.pb")
OUT=Path("data/diagnostics/gtfs_sweden3_realtime.json")
def check(operator,feed):
    req=Request(f"{BASE}/{operator}/{feed}?"+urlencode({"key":KEY}),
                headers={"User-Agent":"Lulea-statistik/GTFS-Sweden3-test","Accept":"application/x-protobuf"})
    try:
        with urlopen(req,timeout=30) as resp:
            first=resp.read(1024)
            return {"http_status":resp.status,"content_type":resp.headers.get("Content-Type"),
                    "content_length":resp.headers.get("Content-Length"),"first_kb_bytes":len(first),
                    "protobuf_candidate":bool(first) and not first.startswith((b"{",b"<",b"["))}
    except HTTPError as exc:return {"http_status":exc.code,"error":"http_error"}
    except (URLError,TimeoutError) as exc:return {"error":type(exc).__name__}
def main():
    if not KEY:raise SystemExit("Missing GitHub secret GTFS_SWEDEN_3_REALTIME")
    result={"checked_utc":datetime.now(timezone.utc).isoformat(),"dataset":"GTFS Sweden 3 Realtime",
            "operators":{op:{feed:check(op,feed) for feed in FEEDS} for op in OPERATORS},
            "note":"SL is a control operator. No GTFS protobuf body, exact URL or API token is stored. HTTP 200 does not establish Norrbotten service coverage."}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

# Initial GTFS Sweden 3 realtime verification.
