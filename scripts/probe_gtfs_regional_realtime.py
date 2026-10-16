#!/usr/bin/env python3
"""One-shot GTFS Regional Realtime availability probe; never store API keys or vehicle positions."""
import json, os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
KEY=os.environ.get("TRAFIKLAB_GTFS_REGIONAL_REALTIME")
OUT=Path("data/diagnostics/gtfs_regional_realtime_availability.json")
OPERATORS=("norrbotten","lulea")
FEEDS=("TripUpdates.pb","VehiclePositions.pb")
def probe(operator,feed):
    base="https://opendata.samtrafiken.se/gtfs-rt/"+operator+"/"+feed
    request=Request(base+"?"+urlencode({"key":KEY}),headers={"User-Agent":"Lulea-statistik/GTFS-RT-availability-audit"})
    try:
        with urlopen(request,timeout=25) as response:
            raw=response.read(2_000_001)
            return {"status":response.status,"content_type":response.headers.get("Content-Type"),
                    "bytes_read":len(raw),"truncated":len(raw)>2_000_000,
                    "protobuf_candidate":bool(raw) and not raw.startswith((b"{",b"<",b"["))}
    except HTTPError as ex:
        # Do not include HTTP response body or URLs: they may expose key values.
        return {"status":ex.code,"error":"http_error"}
    except (URLError,TimeoutError) as ex:
        return {"status":None,"error":type(ex).__name__}
def main():
    if not KEY:
        raise SystemExit("Missing GitHub Actions secret TRAFIKLAB_GTFS_REGIONAL_REALTIME")
    report={"checked_utc":datetime.now(timezone.utc).isoformat(),
            "dataset":"GTFS Regional Realtime","scope":"Norrbotten and Lulea public transport only",
            "warning":"This is NOT road traffic volume. HTTP 200 does not guarantee actual operator observations.",
            "results":{}}
    for operator in OPERATORS:
        report["results"][operator]={feed:probe(operator,feed) for feed in FEEDS}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
