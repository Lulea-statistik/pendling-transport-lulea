#!/usr/bin/env python3
"""Intersect NVDB road traffic segments with the ordinary posted speed-limit network.
One measurement feature may overlap another; this is a diagnostic, not audited VKT.
"""
import json, os, sqlite3, sys, tempfile, zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.ops import unary_union
from shapely.strtree import STRtree
from build_nvdb_five_municipalities import gpkg_geom, quote
from analyze_nvdb_attribute_diagnostics import region_geometries
from inspect_lastkajen_norrbotten import api, BASE, PACKAGE_ID, FILE_NAME

SPEED_LAYER="NVDB_DK_O_48_Hastighetsgrans"
TRAFFIC_LAYER="TRAFIK_DK_O_105_Trafik"
MANAGER_LAYER="NVDB_DK_O_2_Vaghallare"
def fields(con,table):
    return [r[1] for r in con.execute("PRAGMA table_info("+quote(table)+")")]
def layer(con,table):
    row=con.execute("SELECT column_name,srs_id FROM gpkg_geometry_columns WHERE table_name=?",(table,)).fetchone()
    if not row or row[1]!=3006:raise ValueError("Missing EPSG:3006 layer "+table)
    return row[0]
def numeric(v):
    try:
        number=float(v)
        return number if 0<=number<=1000000 else None
    except (TypeError,ValueError):return None
def fetch_segments(con,table,geometry_column,attribute,validate):
    sql="SELECT "+quote(geometry_column)+","+quote(attribute)+" FROM "+quote(table)
    out=[]
    for blob,value in con.execute(sql):
        g=gpkg_geom(blob)
        if g is None or g.is_empty or not g.is_valid:continue
        value=validate(value)
        if value is None or g.geom_type not in ("LineString","MultiLineString"):continue
        out.append((g,value))
    return out
def road_maintainer_inventory(con):
    """Inspect actual Lastkajen schema before attempting a road-manager join."""
    layers=con.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns").fetchall()
    relevant=[]
    for table,geom,srs in layers:
        if any(part in table.lower() for part in ("vaghall","vag_hall","roadowner","vagagare")):
            cols=fields(con,table)
            selected=[c for c in cols if c!=geom and any(x in c.lower() for x in ("vaghall","agare","typ","kategori"))]
            counts={}
            for col in selected[:8]:
                rows=con.execute("SELECT "+quote(col)+",COUNT(*) FROM "+quote(table)+" GROUP BY "+quote(col)+" ORDER BY COUNT(*) DESC LIMIT 15").fetchall()
                counts[col]=[{"value":str(val) if val is not None else None,"features":n} for val,n in rows]
            relevant.append({"layer":table,"geom_column":geom,"srs_id":srs,"all_columns":cols,"distribution":counts})
    return relevant

def run(con,municipalities):
    speed_geom=layer(con,SPEED_LAYER);traffic_geom=layer(con,TRAFFIC_LAYER)
    manager_geom=layer(con,MANAGER_LAYER)
    speed_attr="Hogsta_tillatna_hastighet"
    adt_attr="Adt_samtliga_fordon"
    if speed_attr not in fields(con,SPEED_LAYER) or adt_attr not in fields(con,TRAFFIC_LAYER):
        raise ValueError("Required ordinary speed or ADT column is unavailable")
    speed=fetch_segments(con,SPEED_LAYER,speed_geom,speed_attr,lambda x:int(x) if numeric(x) is not None and 5<=float(x)<=140 else None)
    traffic=fetch_segments(con,TRAFFIC_LAYER,traffic_geom,adt_attr,numeric)
    if not speed or not traffic:raise ValueError("No relevant speed or traffic data")
    manager=fetch_segments(con,MANAGER_LAYER,manager_geom,"Vaghallartyp",
        lambda x:str(x).strip().lower() if x is not None and str(x).strip().lower() in ("statlig","kommunal","enskild") else None)
    if not manager:raise ValueError("No valid road manager segments")
    manager_tree=STRtree([x[0] for x in manager])
    geometries=[x[0] for x in speed];tree=STRtree(geometries)
    out={}
    for code,name,boundary,prepared in municipalities:
        bins=defaultdict(lambda:{"traffic_exposure_vehicle_km_per_day":0.0,"covered_length_km":0.0,"traffic_features":0})
        total_traffic_km=matched_km=ambiguous_km=unmatched_km=0.0
        manager_bins=defaultdict(lambda:defaultdict(lambda:{"traffic_exposure_vehicle_km_per_day":0.0,"covered_length_km":0.0}))
        manager_unmatched_km=manager_ambiguous_km=0.0
        features=0
        for road,adt in traffic:
            if not prepared.intersects(road):continue
            segment=road.intersection(boundary)
            if segment.is_empty or segment.length<=0:continue
            features+=1;total_traffic_km+=segment.length/1000
            # Union the intersection of each speed class with this traffic feature.
            class_parts=defaultdict(list)
            for idx in tree.query(segment):
                speed_road,limit=speed[int(idx)]
                if not speed_road.intersects(segment):continue
                crossing=speed_road.intersection(segment)
                if crossing.length>0:class_parts[limit].append(crossing)
            if not class_parts:
                unmatched_km+=segment.length/1000
                continue
            class_lines={limit:unary_union(parts) for limit,parts in class_parts.items()}
            # Exclude overlaps with a different posted-speed class rather than double count.
            other_classes=list(class_lines.items())
            for limit,line in other_classes:
                conflicting=[other for speed_class,other in other_classes if speed_class!=limit]
                if conflicting:line=line.difference(unary_union(conflicting))
                distance=line.length/1000
                if distance<=0:continue
                bins[str(limit)]["traffic_exposure_vehicle_km_per_day"]+=adt*distance
                bins[str(limit)]["covered_length_km"]+=distance
                bins[str(limit)]["traffic_features"]+=1
                matched_km+=distance
                by_manager=defaultdict(list)
                for midx in manager_tree.query(line):
                    mg,category=manager[int(midx)]
                    if not mg.intersects(line):continue
                    shared=mg.intersection(line)
                    if shared.length>0:by_manager[category].append(shared)
                if not by_manager:
                    manager_unmatched_km+=distance
                    continue
                merged={cat:unary_union(parts) for cat,parts in by_manager.items()}
                assigned=0.0
                for cat,part in merged.items():
                    conflicts=[other for othercat,other in merged.items() if othercat!=cat]
                    unique=part.difference(unary_union(conflicts)) if conflicts else part
                    km=unique.length/1000
                    if km<=0:continue
                    cell=manager_bins[str(limit)][cat]
                    cell["covered_length_km"]+=km
                    cell["traffic_exposure_vehicle_km_per_day"]+=adt*km
                    assigned+=km
                possible=unary_union(list(merged.values())).length/1000
                manager_ambiguous_km+=max(0,possible-assigned)
                manager_unmatched_km+=max(0,distance-possible)
            available=unary_union(list(class_lines.values())).length/1000
            ambiguous_km+=max(0,available-sum(
                class_lines[limit].difference(unary_union([other for x,other in other_classes if x!=limit])).length/1000
                if len(other_classes)>1 else class_lines[limit].length/1000 for limit in class_lines))
            unmatched_km+=max(0,segment.length/1000-available)
        bins_output=[]
        for limit,vals in sorted(bins.items(),key=lambda x:int(x[0])):
            exposure=vals["traffic_exposure_vehicle_km_per_day"]
            km=vals["covered_length_km"]
            bins_output.append({"speed_kmh":int(limit),
                "traffic_exposure_vehicle_km_per_day":round(exposure,2),
                "length_weighted_adt":round(exposure/km,1) if km else None,
                "covered_length_km":round(km,3),
                "traffic_feature_intersections":vals["traffic_features"]})
        manager_by_speed={}
        for speed_class,categories in manager_bins.items():
            manager_by_speed[speed_class]={}
            for category,values in categories.items():
                km=values["covered_length_km"]
                exposure=values["traffic_exposure_vehicle_km_per_day"]
                manager_by_speed[speed_class][category]={
                    "covered_length_km":round(km,3),
                    "traffic_exposure_vehicle_km_per_day":round(exposure,2),
                    "length_weighted_adt":round(exposure/km,1) if km else None}
        out[code]={"name":name,"speed_classes":bins_output,
                   "manager_by_speed":manager_by_speed,
                   "manager_unmatched_km":round(manager_unmatched_km,3),
                   "manager_ambiguous_km":round(manager_ambiguous_km,3),
                   "traffic_features_intersecting":features,
                   "traffic_source_length_km":round(total_traffic_km,3),
                   "matched_length_km":round(matched_km,3),
                   "ambiguous_speed_length_km":round(ambiguous_km,3),
                   "without_speed_match_km":round(unmatched_km,3)}
        print("Calculated",name,features,"traffic features",len(bins_output),"speed classes")
    return out
def main():
    regions=region_geometries()
    username=os.getenv("LASTKAJEN_USERNAME");password=os.getenv("LASTKAJEN_PASSWORD")
    if not username or not password:raise ValueError("Missing credentials")
    login=api("/Identity/Login",form={"UserName":username,"Password":password})
    bearer=login.get("access_token")
    if not bearer:raise RuntimeError("No access token")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    if not isinstance(ticket,str):raise ValueError("Invalid download token response")
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"nvdb.zip"
        total=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as response,path.open("wb") as output:
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>1_500_000_000:raise RuntimeError("Archive too large")
                output.write(block)
        with zipfile.ZipFile(path) as archive:
            parts=[x for x in archive.infolist() if not x.is_dir() and x.filename.lower().endswith(".gpkg")]
            if len(parts)!=1 or parts[0].file_size>8_000_000_000:raise ValueError("Unexpected GeoPackage content")
            dbpath=Path(tmp)/"nvdb.gpkg"
            with archive.open(parts[0]) as src,dbpath.open("wb") as dst:
                while b:=src.read(1024*1024):dst.write(b)
            con=sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True)
            try:
                manager_inventory=road_maintainer_inventory(con)
                data=run(con,regions)
            finally:con.close()
    dest=Path("nvdb_output");dest.mkdir(exist_ok=True)
    (dest/"traffic_by_speed_diagnostics.json").write_text(json.dumps({
        "status":"preliminary","package_id":PACKAGE_ID,
        "road_maintainer_schema_inventory":manager_inventory,
        "source":"NVDB Lastkajen Norrbottens län",
        "analysis_crs":"EPSG:3006",
        "units":{"traffic_exposure":"vehicle-km/day","length_weighted_adt":"vehicles/day"},
        "limitations":"Road manager classified from Vaghallartyp; conflicting categories excluded. Only NVDB traffic features with ordinary speed geometry matching; no deduplication of overlapping traffic features; excludes conflicts between speed classes and unmatched lengths; cannot isolate passenger cars from all motor vehicles.",
        "municipalities":data},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":
    try:main()
    except Exception as exc:print("NVDB speed-traffic overlay failed:",str(exc),file=sys.stderr);sys.exit(1)
