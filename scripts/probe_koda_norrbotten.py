#!/usr/bin/env python3
"""Small KoDa archive availability probe. No API key or raw personal/location data is saved."""
import json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

BASE="https://api.koda.trafiklab.se/KoDa/api/v2/gtfs-rt"
OUT=Path("data/diagnostics/koda_norrbotten_availability.json")
FEEDS=("VehiclePositions","TripUpdates","ServiceAlerts")
def check(operator,feed,day,key):
    url=f"{BASE}/{operator}/{feed}?"+urlencode({"date":day,"hour":"12","key":key})
    request=Request(url,headers={"User-Agent":"Lulea-statistik/KoDa-availability-audit"})
    try:
        with urlopen(request,timeout=45) as response:
            # Read only a short prefix. Never store the raw feed, URL or token.
            prefix=response.read(64)
            return {"http_status":response.status,"content_type":response.headers.get("Content-Type"),
                    "content_length_header":response.headers.get("Content-Length"),
                    "received_prefix_bytes":len(prefix)}
    except HTTPError as exc:
        return {"http_status":exc.code,"result":"http_error"}
    except (URLError,TimeoutError) as exc:
        return {"result":type(exc).__name__}
def main():
    key=os.environ.get("KOLLEKTIVTRAFIKENS_DATALABB_KODA","").strip()
    if not key:raise SystemExit("Missing KOLLEKTIVTRAFIKENS_DATALABB_KODA GitHub secret")
    day=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
    result={"checked_utc":datetime.now(timezone.utc).isoformat(),"historical_day":day,
            "hour_utc":"12","operator":"norrbotten","purpose":"archive existence only; not proof of bus service on road 97",
            "feeds":{name:check("norrbotten",name,day,key) for name in FEEDS}}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
