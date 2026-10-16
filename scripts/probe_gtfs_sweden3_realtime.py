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
def safe_structure(payload):
    """Report structural labels only, never API response values."""
    try:
        data=json.loads(payload.decode("utf-8"))
    except (ValueError,UnicodeError):
        return {"json_type":"unparseable"}
    if not isinstance(data,dict):
        return {"json_type":type(data).__name__}
    permitted={"error","message","code","status","detail","details","type","title",
               "errors","requestId","timestamp","path","reason"}
    keys=sorted(k for k in data if k in permitted)
    types={k:type(data[k]).__name__ for k in keys}
    return {"json_type":"object","recognized_keys":keys,
            "recognized_value_types":types,
            "other_key_names":[k for k in sorted(data) if k not in permitted and k.isidentifier() and len(k)<=64][:20],
            "has_other_keys":bool(set(data)-permitted)}

def classify_message(payload):
    """Classify server error text without writing any of it to logs or artifacts."""
    try:
        obj=json.loads(payload.decode("utf-8"))
    except (ValueError,UnicodeError):
        return "unreadable_response"
    message=obj.get("errorMessage","") if isinstance(obj,dict) else ""
    if not isinstance(message,str):return "no_text_message"
    msg=message.casefold()
    if any(t in msg for t in ("invalid api key","invalid key","api key is invalid","ogiltig nyckel")):
        return "invalid_api_key"
    if any(t in msg for t in ("missing api key","key is missing","api key required","no api key")):
        return "missing_api_key"
    if any(t in msg for t in ("not authorized","unauthorized","access denied","does not have access","not permitted","subscription","not subscribed","not allowed","permission","product access")):
        return "product_access_denied"
    if any(t in msg for t in ("unknown endpoint","not found","invalid url","unsupported path","invalid resource","invalid request","unknown operator")):
        return "invalid_endpoint_or_resource"
    if any(t in msg for t in ("rate limit","too many requests","quota exceeded")):
        return "rate_limited"
    return "unknown_error_message"

def classify_error(payload):
    """Only allow fixed diagnostic labels; never persist arbitrary server text."""
    try:
        data=json.loads(payload.decode("utf-8"))
    except (ValueError,UnicodeError):
        return "unstructured_error"
    if not isinstance(data,dict):
        return "unstructured_error"
    code=data.get("error")
    if isinstance(code,dict):
        code=code.get("code") or code.get("key")
    if not isinstance(code,str):
        return "json_error_without_code"
    allowed={"error.key.invalid","error.key.missing","error.key.expired",
             "error.key.unauthorized","error.key.no_access",
             "invalid_api_key","access_denied","unauthorized",
             "not_acceptable","not_found"}
    return code if code in allowed else "other_json_error"

def check(operator,feed):
    req=Request(f"{BASE}/{operator}/{feed}?"+urlencode({"key":KEY}),
                headers={"User-Agent":"Lulea-statistik/GTFS-Sweden3-test","Accept":"application/x-protobuf"})
    try:
        with urlopen(req,timeout=30) as resp:
            first=resp.read(1024)
            return {"http_status":resp.status,"content_type":resp.headers.get("Content-Type"),
                    "content_length":resp.headers.get("Content-Length"),"first_kb_bytes":len(first),
                    "protobuf_candidate":bool(first) and not first.startswith((b"{",b"<",b"["))}
    except HTTPError as exc:
        content_type=(exc.headers.get("Content-Type") or "").split(";")[0].lower()
        payload=exc.read(2048)
        return {"http_status":exc.code,"error_type":classify_error(payload),
                "message_category":classify_message(payload),
                "json_structure":safe_structure(payload),
                "response_content_type":content_type if content_type in ("application/json","text/plain","text/html") else "other",
                "retry_after_present":bool(exc.headers.get("Retry-After"))}
    except (URLError,TimeoutError) as exc:return {"error":type(exc).__name__}
def main():
    if not KEY:raise SystemExit("Missing GitHub secret GTFS_SWEDEN_3_REALTIME")
    result={"checked_utc":datetime.now(timezone.utc).isoformat(),"dataset":"GTFS Sweden 3 Realtime",
            "single_probe":{"operator":"sl","feed":"TripUpdatesSweden.pb","result":check("sl","TripUpdatesSweden.pb")},
            "note":"One request only. Only JSON field names and types are logged, never response values or API keys."}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

# Initial GTFS Sweden 3 realtime verification.
