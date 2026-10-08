from __future__ import annotations

import csv
import io
import json
import math
import os
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

BOUNDARY_URL="https://raw.githubusercontent.com/okfse/sweden-geojson/master/swedish_municipalities.geojson"
GTFS_URL="https://api.resrobot.se/gtfs/sweden.zip?key={key}"

def fetch_bytes(url: str) -> bytes:
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0"})
    with urlopen(req,timeout=180) as r:
        return r.read()

def fetch_json(url: str):
    return json.loads(fetch_bytes(url).decode("utf-8"))

def point_in_ring(lon,lat,ring):
    inside=False
    j=len(ring)-1
    for i in range(len(ring)):
        xi,yi=ring[i][0],ring[i][1]
        xj,yj=ring[j][0],ring[j][1]
        intersects=((yi>lat)!=(yj>lat)) and (lon < (xj-xi)*(lat-yi)/((yj-yi) or 1e-20)+xi)
        if intersects:
            inside=not inside
        j=i
    return inside

def point_in_polygon(lon,lat,coords):
    if not coords:
        return False
    if not point_in_ring(lon,lat,coords[0]):
        return False
    for hole in coords[1:]:
        if point_in_ring(lon,lat,hole):
            return False
    return True

def point_in_geometry(lon,lat,geom):
    gtype=geom.get("type")
    coords=geom.get("coordinates",[])
    if gtype=="Polygon":
        return point_in_polygon(lon,lat,coords)
    if gtype=="MultiPolygon":
        return any(point_in_polygon(lon,lat,p) for p in coords)
    return False

def read_txt(zf,name):
    try:
        raw=zf.read(name)
    except KeyError:
        return []
    text=raw.decode("utf-8-sig",errors="replace")
    return list(csv.DictReader(io.StringIO(text)))

def next_weekday(d: date, weekday=0):
    delta=(weekday-d.weekday())%7
    if delta==0:
        delta=7
    return d+timedelta(days=delta)

def ymd(s):
    try:
        return date(int(s[:4]),int(s[4:6]),int(s[6:8]))
    except Exception:
        return None

def active_services(zf, target: date):
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
        d=ymd(r.get("date",""))
        if d!=target:
            continue
        sid=r.get("service_id","")
        if r.get("exception_type")=="1":
            active.add(sid)
        elif r.get("exception_type")=="2":
            active.discard(sid)
    return active

def hhmm_to_seconds(v):
    try:
        h,m,s=[int(x) for x in v.split(":")]
        return h*3600+m*60+s
    except Exception:
        return None

def main():
    key=os.environ.get("TRAFIKLAB_API_KEY","").strip()
    today=date.today()
    target=next_weekday(today,0)

    base_out={
        "configured":bool(key),
        "generated":today.isoformat(),
        "reference_weekday":target.isoformat(),
        "source":"Trafiklab GTFS Sverige 2 / Samtrafiken",
        "municipality":"Luleå",
        "operators":[],
        "summary":{},
        "routes":[],
        "stops":[],
        "note":"",
    }

    if not key:
        base_out["note"]="TRAFIKLAB_API_KEY saknas i GitHub Actions secrets."
        for p in [Path("data/transit.json"),Path("docs/data/transit.json")]:
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(base_out,ensure_ascii=False,indent=2),encoding="utf-8")
        print(base_out["note"])
        return

    boundary=fetch_json(BOUNDARY_URL)
    feature=next(
        (f for f in boundary.get("features",[])
         if str(f.get("properties",{}).get("id",""))=="2580"
         or str(f.get("properties",{}).get("kom_namn","")).casefold()=="luleå"),
        None
    )
    if not feature:
        raise RuntimeError("Kunde inte hitta Luleå kommun i kommunpolygonen.")
    geom=feature["geometry"]

    all_stops={}
    route_records=[]
    stop_departures=Counter()
    stop_routes=defaultdict(set)

    raw=fetch_bytes(GTFS_URL.format(key=key))
    zf=zipfile.ZipFile(io.BytesIO(raw))
    stops=read_txt(zf,"stops.txt")
    routes=read_txt(zf,"routes.txt")
    trips=read_txt(zf,"trips.txt")
    stop_times=read_txt(zf,"stop_times.txt")
    agencies=read_txt(zf,"agency.txt")

    agency_by_id={a.get("agency_id",""):a for a in agencies}
    route_by_id={r.get("route_id",""):r for r in routes}
    allowed_agencies={
        aid for aid,a in agency_by_id.items()
        if any(x in (a.get("agency_name","") or "").casefold()
               for x in ("luleå lokaltrafik","länstrafiken norrbotten"))
    }

    def is_bus(route):
        try:
            rt=int(route.get("route_type",""))
        except Exception:
            return False
        return rt==3 or 700<=rt<800

    selected={}
    for r in stops:
        try:
            lat=float(r.get("stop_lat",""))
            lon=float(r.get("stop_lon",""))
        except Exception:
            continue
        if point_in_geometry(lon,lat,geom):
            sid=r.get("stop_id","")
            selected[sid]={
                "id":sid,
                "name":r.get("stop_name","") or sid,
                "lat":lat,
                "lon":lon,
                "location_type":r.get("location_type",""),
                "parent_station":r.get("parent_station",""),
            }

    services=active_services(zf,target)
    trips_by_id={}
    for r in trips:
        if services and r.get("service_id","") not in services:
            continue
        route=route_by_id.get(r.get("route_id",""),{})
        if not is_bus(route):
            continue
        if route.get("agency_id","") not in allowed_agencies:
            continue
        trips_by_id[r.get("trip_id","")]=r

    trip_ids_at_selected=set()
    for st in stop_times:
        sid=st.get("stop_id","")
        tid=st.get("trip_id","")
        if sid not in selected or tid not in trips_by_id:
            continue
        trip_ids_at_selected.add(tid)
        stop_departures[sid]+=1
        rid=trips_by_id[tid].get("route_id","")
        if rid:
            stop_routes[sid].add(rid)

    relevant_route_ids={trips_by_id[tid].get("route_id","") for tid in trip_ids_at_selected}
    trip_counts=Counter(trips_by_id[tid].get("route_id","") for tid in trip_ids_at_selected)

    agency_summary=defaultdict(lambda: {"routes":set(),"trips":set(),"stops":set()})
    for rid in relevant_route_ids:
        if not rid:
            continue
        r=route_by_id.get(rid,{})
        agency_id=r.get("agency_id","")
        agency=agency_by_id.get(agency_id,{})
        label=agency.get("agency_name","") or agency_id or "Okänd operatör"
        route_records.append({
            "id":rid,
            "agency_id":agency_id,
            "operator_label":label,
            "route_id":rid,
            "short_name":r.get("route_short_name",""),
            "long_name":r.get("route_long_name",""),
            "route_type":r.get("route_type",""),
            "weekday_trips":trip_counts.get(rid,0),
        })
        agency_summary[label]["routes"].add(rid)

    for sid,rec in selected.items():
        rec["weekday_departures"]=stop_departures[sid]
        rec["routes"]=len(stop_routes[sid])
        all_stops[sid]=rec

    for tid in trip_ids_at_selected:
        trip=trips_by_id[tid]
        rid=trip.get("route_id","")
        route=route_by_id.get(rid,{})
        agency_id=route.get("agency_id","")
        label=agency_by_id.get(agency_id,{}).get("agency_name","") or agency_id or "Okänd operatör"
        agency_summary[label]["trips"].add(tid)
    for sid in selected:
        for rid in stop_routes[sid]:
            route=route_by_id.get(rid,{})
            agency_id=route.get("agency_id","")
            label=agency_by_id.get(agency_id,{}).get("agency_name","") or agency_id or "Okänd operatör"
            agency_summary[label]["stops"].add(sid)

    operator_summary=[
        {
            "label":label,
            "stops":len(v["stops"]),
            "routes":len(v["routes"]),
            "weekday_trips":len(v["trips"]),
        }
        for label,v in sorted(agency_summary.items())
    ]

    routes_sorted=sorted(route_records,key=lambda r:(r["operator_label"],r["short_name"],r["long_name"]))
    stops_sorted=sorted(all_stops.values(),key=lambda r:(-r["weekday_departures"],r["name"]))

    base_out.update({
        "configured":True,
        "operators":operator_summary,
        "summary":{
            "stops":len(stops_sorted),
            "routes":len({r["id"] for r in routes_sorted}),
            "weekday_departures":sum(r["weekday_departures"] for r in stops_sorted),
            "operators":len(operator_summary),
        },
        "routes":routes_sorted,
        "stops":stops_sorted,
        "note":"GTFS Sverige 2 har filtrerats till busslinjer med hållplatser inom Luleå kommuns polygon. Avgångar avser nästa måndag med aktivt GTFS-utbud.",
    })

    for p in [Path("data/transit.json"),Path("docs/data/transit.json")]:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(base_out,ensure_ascii=False,indent=2),encoding="utf-8")

    print(json.dumps(base_out["summary"],ensure_ascii=False))

if __name__=="__main__":
    main()
