#!/usr/bin/env python3
"""One-shot, read-only TrafficFlow coverage probe for road 97 (Lulea-Boden).

This probes the Trafikinfo v2 API, not the newer Data Cache Query API.
A measurement cannot be attributed to road 97 from a bounding box alone.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.sax.saxutils import escape

ENDPOINT = "https://api.trafikinfo.trafikverket.se/v2/data.json"
OUT = Path("data/diagnostics/road97_trafficflow_probe.json")
# Approximate corridor envelope, for *candidate discovery only*.
BBOX = {"south":65.54,"north":65.89,"west":21.55,"east":22.25}

def request(key, filtering=True):
    # The box uses latitude-longitude in Trafikinfo's WGS84 filter format.
    within = ('<FILTER><WITHIN name="Geometry.WGS84" shape="box" '
              'value="65.54 21.55,65.89 22.25" /></FILTER>') if filtering else ""
    body = ('<REQUEST><LOGIN authenticationkey="'+escape(key, {'"':'&quot;'})+'"/>'
            '<QUERY objecttype="TrafficFlow" schemaversion="1.4" limit="500">'
            +within+'</QUERY></REQUEST>').encode("utf-8")
    req = Request(ENDPOINT, data=body, headers={"Content-Type":"text/xml","Accept":"application/json",
                                                   "User-Agent":"Lulea-statistik/road97-coverage-probe"})
    with urlopen(req,timeout=55) as response:
        return json.load(response)

def error_messages(payload):
    out=[]
    if isinstance(payload,dict):
        for result in payload.get("RESPONSE",{}).get("RESULT",[]):
            if isinstance(result,dict) and result.get("ERROR"):
                out.append(str(result["ERROR"])[:500])
    return out

def rows(payload):
    result=payload.get("RESPONSE",{}).get("RESULT",[]) if isinstance(payload,dict) else []
    result=result if isinstance(result,list) else [result]
    values=[]
    for x in result:
        if isinstance(x,dict):
            v=x.get("TrafficFlow",[])
            values.extend(v if isinstance(v,list) else ([v] if isinstance(v,dict) else []))
    return values

def main():
    key=os.environ.get("TRAFIKVERKET_API_KEY","").strip()
    if not key:
        print("Missing secret TRAFIKVERKET_API_KEY",file=sys.stderr)
        return 2
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"Road 97, Lulea-Boden candidate bounding box",
            "bbox_wgs84":BBOX,"api":ENDPOINT,"objecttype":"TrafficFlow",
            "schema_version":"1.4","limits":["Spatially nearby does not establish road number",
            "A zero result is not proof of absent measurements",
            "Trafikinfo v2 and Data Cache use different endpoints"]}
    try:
        response=request(key,True)
        errors=error_messages(response)
        report["spatial_filter_errors"]=errors
        if errors:
            # A limited unfiltered query only diagnoses API/key/schema availability.
            response=request(key,False)
            report["fallback"]="unfiltered diagnostic, not geographic coverage"
        else:
            report["fallback"]=None
        report["api_errors"]=error_messages(response)
        found=rows(response)
        report["returned_records"]=len(found)
        report["sample_keys"]=sorted(set().union(*(x.keys() for x in found[:10]))) if found else []
        # No raw personal/secrets or full nationwide API response saved.
        report["sample_objects"]=found[:3]
        report["status"]="api_error" if report["api_errors"] else ("unfiltered_only" if errors else "spatial_query_ok")
    except (HTTPError,URLError,TimeoutError,ValueError) as exc:
        report["status"]="request_failed"
        report["error"]=str(exc)[:300]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="sample_objects"},ensure_ascii=False,indent=2))
    return 1 if report["status"] in ("api_error","request_failed") else 0

if __name__=="__main__":
    raise SystemExit(main())
