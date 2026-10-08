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
REGIONAL_OPERATORS={
    "lulea":"Luleå Lokaltrafik",
    "norrbotten":"Länstrafiken Norrbotten",
}

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
        "source":"Trafiklab GTFS Regional / Samtrafiken",
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
    operator_summary=[]

    for op,label in REGIONAL_OPERATORS.items():
        url=f"https://opendata.samtrafiken.se/gtfs/{op}/{op}.zip?key={key}"
        raw=fetch_bytes(url)
        zf=zipfile.ZipFile(io.BytesIO(raw))

        stops=read_txt(zf,"stops.txt")
        routes=read_txt(zf,"routes.txt")
        trips=read_txt(zf,"trips.txt")
        stop_times=read_txt(zf,"stop_times.txt")
        agencies=read_txt(zf,"agency.txt")

        route_by_id={r.get("route_id",""):r for r in routes}
        services=active_services(zf,target)

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
                    "id":f"{op}:{sid}",
                    "operator":op,
                    "operator_label":label,
                    "name":r.get("stop_name","") or sid,
                    "lat":lat,
                    "lon":lon,
                    "location_type":r.get("location_type",""),
                    "parent_station":r.get("parent_station",""),
                }

        trips_by_id={}
        for r in trips:
            if services and r.get("service_id","") not in services:
                continue
            route=route_by_id.get(r.get("route_id",""),{})
            if not is_bus(route):
                continue
            trips_by_id[r.get("trip_id","")]=r

        trip_ids_at_selected=set()
        for st in stop_times:
            sid=st.get("stop_id","")
            tid=st.get("trip_id","")
            if sid not in selected or tid not in trips_by_id:
                continue
            trip_ids_at_selected.add(tid)
            stop_key=f"{op}:{sid}"
            stop_departures[stop_key]+=1
            rid=trips_by_id[tid].get("route_id","")
            if rid:
                stop_routes[stop_key].add(f"{op}:{rid}")

        relevant_route_ids={trips_by_id[tid].get("route_id","") for tid in trip_ids_at_selected}
        trip_counts=Counter(trips_by_id[tid].get("route_id","") for tid in trip_ids_at_selected)

        for rid in relevant_route_ids:
            if not rid:
                continue
            r=route_by_id.get(rid,{})
            route_records.append({
                "id":f"{op}:{rid}",
                "operator":op,
                "operator_label":label,
                "route_id":rid,
                "short_name":r.get("route_short_name",""),
                "long_name":r.get("route_long_name",""),
                "route_type":r.get("route_type",""),
                "weekday_trips":trip_counts.get(rid,0),
            })

        for sid,rec in selected.items():
            key2=f"{op}:{sid}"
            rec["weekday_departures"]=stop_departures[key2]
            rec["routes"]=len(stop_routes[key2])
            all_stops[key2]=rec

        operator_summary.append({
            "operator":op,
            "label":label,
            "stops":len(selected),
            "routes":len(relevant_route_ids),
            "weekday_trips":len(trip_ids_at_selected),
            "agency_names":[a.get("agency_name","") for a in agencies if a.get("agency_name")],
            "source_url":url.split("?")[0],
        })

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
        "note":"Aktuell data hämtas direkt från GTFS Regional för Luleå Lokaltrafik och Länstrafiken Norrbotten. Hållplatser filtreras mot Luleå kommuns polygon. Avgångar avser nästa måndag med aktivt GTFS-utbud.",
    })

    for p in [Path("data/transit.json"),Path("docs/data/transit.json")]:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(base_out,ensure_ascii=False,indent=2),encoding="utf-8")

    print(json.dumps(base_out["summary"],ensure_ascii=False))

if __name__=="__main__":
    main()
