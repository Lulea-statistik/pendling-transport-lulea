from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from html.parser import HTMLParser

ARCHIVE_ROOT="https://data.samtrafiken.se/trafiklab/gtfs-sverige-2/"
BOUNDARY_URL="https://raw.githubusercontent.com/okfse/sweden-geojson/master/swedish_municipalities.geojson"
OUT=Path("data/transit_history.json")
WEB=Path("docs/data/transit_history.json")

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag!="a":
            return
        for k,v in attrs:
            if k=="href":
                self.links.append(v)

def fetch_bytes(url):
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0"})
    with urlopen(req,timeout=180) as r:
        return r.read()

def fetch_text(url):
    return fetch_bytes(url).decode("utf-8",errors="replace")

def fetch_json(url):
    return json.loads(fetch_bytes(url).decode("utf-8"))

def links(url):
    p=LinkParser()
    p.feed(fetch_text(url))
    return p.links

def point_in_ring(lon,lat,ring):
    inside=False
    j=len(ring)-1
    for i in range(len(ring)):
        xi,yi=ring[i][0],ring[i][1]
        xj,yj=ring[j][0],ring[j][1]
        if ((yi>lat)!=(yj>lat)) and lon < (xj-xi)*(lat-yi)/((yj-yi) or 1e-20)+xi:
            inside=not inside
        j=i
    return inside

def point_in_polygon(lon,lat,coords):
    if not coords or not point_in_ring(lon,lat,coords[0]):
        return False
    return not any(point_in_ring(lon,lat,hole) for hole in coords[1:])

def point_in_geometry(lon,lat,geom):
    typ=geom.get("type")
    coords=geom.get("coordinates",[])
    if typ=="Polygon":
        return point_in_polygon(lon,lat,coords)
    if typ=="MultiPolygon":
        return any(point_in_polygon(lon,lat,p) for p in coords)
    return False

def read_txt(zf,name):
    try:
        raw=zf.read(name)
    except KeyError:
        return []
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig",errors="replace"))))

def ymd(s):
    try:
        return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
    except Exception:
        return None

def next_monday(d):
    return d+timedelta(days=(7-d.weekday())%7)

def active_services(zf,target):
    calendar=read_txt(zf,"calendar.txt")
    exceptions=read_txt(zf,"calendar_dates.txt")
    active=set()
    weekday=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][target.weekday()]
    for r in calendar:
        start=ymd(r.get("start_date",""))
        end=ymd(r.get("end_date",""))
        if start and end and start<=target<=end and r.get(weekday)=="1":
            active.add(r.get("service_id",""))
    for r in exceptions:
        if ymd(r.get("date",""))!=target:
            continue
        sid=r.get("service_id","")
        if r.get("exception_type")=="1":
            active.add(sid)
        elif r.get("exception_type")=="2":
            active.discard(sid)
    return active

def is_bus(route):
    try:
        rt=int(route.get("route_type",""))
    except Exception:
        return False
    return rt==3 or 700<=rt<800

def allowed_agency(name):
    n=(name or "").casefold()
    return "luleå lokaltrafik" in n or "länstrafiken norrbotten" in n

def pick_snapshot(year):
    # Prefer the first available October snapshot for comparability.
    for month in ["10","09","11","08"]:
        base=f"{ARCHIVE_ROOT}{year}/{month}/"
        try:
            candidates=[]
            for href in links(base):
                m=re.fullmatch(r"sweden-(\d{8})\.zip",href.split("/")[-1])
                if m:
                    candidates.append((m.group(1),urljoin(base,href)))
            if candidates:
                candidates.sort()
                return candidates[0]
        except Exception:
            continue
    return None

def analyze_snapshot(url,date_str,geom):
    raw=fetch_bytes(url)
    zf=zipfile.ZipFile(io.BytesIO(raw))
    agencies=read_txt(zf,"agency.txt")
    routes=read_txt(zf,"routes.txt")
    trips=read_txt(zf,"trips.txt")
    stops=read_txt(zf,"stops.txt")
    stop_times=read_txt(zf,"stop_times.txt")

    agency_by_id={a.get("agency_id",""):a for a in agencies}
    route_by_id={r.get("route_id",""):r for r in routes}
    allowed_ids={aid for aid,a in agency_by_id.items() if allowed_agency(a.get("agency_name",""))}

    selected={}
    for r in stops:
        try:
            lat=float(r.get("stop_lat","")); lon=float(r.get("stop_lon",""))
        except Exception:
            continue
        if point_in_geometry(lon,lat,geom):
            selected[r.get("stop_id","")]=r

    snap_date=date(int(date_str[:4]),int(date_str[4:6]),int(date_str[6:8]))
    target=next_monday(snap_date)
    services=active_services(zf,target)

    trips_by_id={}
    for t in trips:
        route=route_by_id.get(t.get("route_id",""),{})
        if route.get("agency_id","") not in allowed_ids or not is_bus(route):
            continue
        if services and t.get("service_id","") not in services:
            continue
        trips_by_id[t.get("trip_id","")]=t

    trip_ids=set()
    stop_ids=set()
    route_ids=set()
    agency_routes=defaultdict(set)
    agency_trips=defaultdict(set)
    agency_stops=defaultdict(set)

    for st in stop_times:
        sid=st.get("stop_id",""); tid=st.get("trip_id","")
        if sid not in selected or tid not in trips_by_id:
            continue
        trip_ids.add(tid); stop_ids.add(sid)
        rid=trips_by_id[tid].get("route_id","")
        if rid:
            route_ids.add(rid)
            agency_id=route_by_id.get(rid,{}).get("agency_id","")
            label=agency_by_id.get(agency_id,{}).get("agency_name","") or agency_id
            agency_routes[label].add(rid)
            agency_trips[label].add(tid)
            agency_stops[label].add(sid)

    operators=[
        {"label":label,"stops":len(agency_stops[label]),"routes":len(agency_routes[label]),"weekday_trips":len(agency_trips[label])}
        for label in sorted(agency_routes)
    ]
    return {
        "snapshot_date":snap_date.isoformat(),
        "reference_weekday":target.isoformat(),
        "stops":len(stop_ids),
        "routes":len(route_ids),
        "weekday_trips":len(trip_ids),
        "operators":operators,
        "source_url":url,
    }

def main():
    boundary=fetch_json(BOUNDARY_URL)
    feature=next((f for f in boundary.get("features",[]) if str(f.get("properties",{}).get("id",""))=="2580"),None)
    if not feature:
        raise RuntimeError("Luleå kommunpolygon saknas.")
    geom=feature["geometry"]

    existing={"source":ARCHIVE_ROOT,"years":[]}
    if OUT.exists():
        try:
            existing=json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    by_year={int(x["year"]):x for x in existing.get("years",[]) if "year" in x}

    current_year=date.today().year
    for year in range(2012,current_year+1):
        if year in by_year and year<current_year:
            continue
        picked=pick_snapshot(year)
        if not picked:
            print("No snapshot",year)
            continue
        date_str,url=picked
        print("Analyserar",year,url)
        try:
            rec=analyze_snapshot(url,date_str,geom)
            rec["year"]=year
            by_year[year]=rec
        except Exception as e:
            print("FAIL",year,repr(e))

    out={
        "source":ARCHIVE_ROOT,
        "method":"Första tillgängliga GTFS Sverige 2-snapshot i oktober, annars närmaste höstmånad. Endast LLT och Länstrafiken Norrbotten, buss, hållplatser inom Luleå kommun.",
        "years":[by_year[y] for y in sorted(by_year)],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); WEB.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(out,ensure_ascii=False,indent=2)
    OUT.write_text(text,encoding="utf-8"); WEB.write_text(text,encoding="utf-8")
    print("År:",[x["year"] for x in out["years"]])

if __name__=="__main__":
    main()
