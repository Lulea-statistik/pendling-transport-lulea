#!/usr/bin/env python3
"""Audit scheduled Lulea-Boden bus departures from GTFS Regional.
Stop-based counts only: NOT verified road 97 passages.
"""
import csv,io,json,os,zipfile
from collections import Counter,defaultdict
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

URL="https://opendata.samtrafiken.se/gtfs/norrbotten/norrbotten.zip"
OUT=Path("data/diagnostics/lulea_boden_gtfs")
TARGET_ROUTES={"28","29","30"}

def rows(z,name):
    try:return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig",errors="replace"))))
    except KeyError:return []

def datecode(s):
    try:return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
    except Exception:return None

def active(z,target):
    flags=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    services=set()
    for r in rows(z,"calendar.txt"):
        start,end=datecode(r.get("start_date","")),datecode(r.get("end_date",""))
        if start and end and start<=target<=end and r.get(flags[target.weekday()])=="1":services.add(r["service_id"])
    for r in rows(z,"calendar_dates.txt"):
        if datecode(r.get("date",""))!=target:continue
        if r.get("exception_type")=="1":services.add(r["service_id"])
        elif r.get("exception_type")=="2":services.discard(r["service_id"])
    return services

def main():
    key=os.environ.get("TRAFIKLAB_API_KEY","").strip()
    if not key:raise SystemExit("Missing TRAFIKLAB_API_KEY")
    req=Request(URL+"?key="+key,headers={"User-Agent":"Lulea-statistik/GTFS-route-audit"})
    try:
        with urlopen(req,timeout=120) as r:data=r.read()
    except HTTPError as exc:
        raise SystemExit(f"GTFS archive HTTP {exc.code}; verify product access")
    z=zipfile.ZipFile(io.BytesIO(data))
    today=date.today()
    target=today+timedelta(days=(7-today.weekday())%7 or 7)
    services=active(z,target)
    routes={r["route_id"]:r for r in rows(z,"routes.txt") if r.get("route_short_name","").strip() in TARGET_ROUTES}
    trips={r["trip_id"]:r for r in rows(z,"trips.txt") if r.get("route_id") in routes and r.get("service_id") in services}
    stops={r["stop_id"]:r for r in rows(z,"stops.txt")}
    tripstops=defaultdict(list)
    for r in rows(z,"stop_times.txt"):
        if r.get("trip_id") in trips:
            tripstops[r["trip_id"]].append(r)
    counts=Counter()
    sample=[]
    for tid,t in trips.items():
        ordered=sorted(tripstops[tid],key=lambda r:int(r.get("stop_sequence") or 0))
        if not ordered:continue
        first,last=stops.get(ordered[0].get("stop_id"),{}),stops.get(ordered[-1].get("stop_id"),{})
        first_name=first.get("stop_name","")
        last_name=last.get("stop_name","")
        time=ordered[0].get("departure_time","") or ordered[0].get("arrival_time","")
        hour=time.split(":")[0] if time else "unknown"
        line=routes[t["route_id"]].get("route_short_name","")
        direction=f"{first_name} -> {last_name}"
        counts[(line,direction,hour)]+=1
        if len(sample)<25:sample.append({"line":line,"from":first_name,"to":last_name,"departure":time,"stop_count":len(ordered),"shape_id":t.get("shape_id")})
    report={"generated_utc":datetime.now(timezone.utc).isoformat(),"reference_date":target.isoformat(),
       "operator":"norrbotten","lines_requested":sorted(TARGET_ROUTES),"lines_found":sorted({r.get("route_short_name") for r in routes.values()}),
       "active_trip_count":len(trips),"trips_with_stops":len(tripstops),"departure_counts_by_line_direction_hour":[{"line":k[0],"direction":k[1],"hour":k[2],"trips":n} for k,n in sorted(counts.items())],
       "samples":sample,"has_shapes": "shapes.txt" in z.namelist(),
       "limitation":"Terminal-to-terminal scheduled service, not observed traffic or measured passage on route 97. For route-level road overlap requires shapes and spatial matching."}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("samples","departure_counts_by_line_direction_hour")},ensure_ascii=False,indent=2))
    print("Route/direction/hour count rows:",len(counts))
if __name__=="__main__":main()
