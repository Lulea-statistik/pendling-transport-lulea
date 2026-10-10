#!/usr/bin/env python3
"""Diagnostic: functional road class x maintainer on the SAME NVDB car-road linework.
All distances EPSG:3006. No raw source geometries are published.
"""
import json,os,sqlite3,sys,tempfile,zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.ops import unary_union
from shapely.strtree import STRtree
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME
from analyze_nvdb_attribute_diagnostics import region_geometries
from build_nvdb_five_municipalities import gpkg_geom,quote

def find_layer(con,suffix):
    matches=[(table,geo,srs) for table,geo,srs in con.execute(
        "SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns")
        if table.lower().endswith("_"+suffix.lower())]
    if len(matches)!=1 or matches[0][2]!=3006:raise ValueError("Unexpected layer or CRS "+suffix+": "+str(matches))
    return matches[0][:2]

def read_lines(con,layer,attr,regions):
    table,geo=find_layer(con,layer)
    columns={r[1] for r in con.execute("PRAGMA table_info("+quote(table)+")")}
    if attr not in columns:raise ValueError("Missing field "+attr+" from "+table)
    grouped={code:defaultdict(list) for code,*_ in regions}
    for geom_blob,value in con.execute("SELECT "+quote(geo)+","+quote(attr)+" FROM "+quote(table)):
        geom=gpkg_geom(geom_blob)
        if geom is None or geom.is_empty or not geom.is_valid or geom.geom_type not in ("LineString","MultiLineString"):continue
        value=str(value).strip().lower() if value is not None else "(saknas)"
        for code,name,boundary,prepared in regions:
            if prepared.intersects(geom):
                clipped=geom.intersection(boundary)
                if clipped.length>0:grouped[code][value].append(clipped)
    result={}
    for code,classes in grouped.items():
        result[code]={c:unary_union(geoms) for c,geoms in classes.items()}
    return result

def compute(con,regions):
    byclass=read_lines(con,"FunkVagklass","Klass",regions)
    byowner=read_lines(con,"Vaghallare","Vaghallartyp",regions)
    outputs={}
    categories=("statlig","kommunal","enskild")
    for code,name,*_ in regions:
        class_shapes=byclass[code]
        class_shapes={k:g for k,g in class_shapes.items() if k.isdigit() and 0<=int(k)<=9 and not g.is_empty}
        owner_shapes=byowner[code]
        maintainer=[(cat,owner_shapes[cat]) for cat in categories if cat in owner_shapes]
        # Within and across categories count unique centerline geometry only.
        total=unary_union(list(class_shapes.values())) if class_shapes else None
        total_m=total.length if total else 0
        details={}
        sum_assigned_m=0.0
        unmatched_m=conflicted_m=0.0
        # Match on precisely shared linework, not a proximity buffer or nearest street.
        for c in sorted(class_shapes,key=int):
            road=class_shapes[c]
            cover={}
            for cat,owner in maintainer:
                common=road.intersection(owner)
                if common.length>0:cover[cat]=common
            category_km={}
            unique_sum=0.0
            for cat,common in cover.items():
                overlapping=[g for other,g in cover.items() if other!=cat]
                exclusive=common.difference(unary_union(overlapping)) if overlapping else common
                km=exclusive.length/1000
                if km>0:category_km[cat]=round(km,3);unique_sum+=exclusive.length
            matched_union=unary_union(list(cover.values())) if cover else None
            seen=matched_union.length if matched_union else 0.0
            class_conflicted=max(0,seen-unique_sum)
            class_unmatched=max(0,road.length-seen)
            conflicted_m+=class_conflicted;unmatched_m+=class_unmatched
            sum_assigned_m+=unique_sum
            details[c]={"car_road_unique_km":round(road.length/1000,3),
                        "maintainer_km":category_km,
                        "not_classified_km":round(class_unmatched/1000,3),
                        "conflicting_maintainers_km":round(class_conflicted/1000,3)}
        # QA: class-wise totals may double count roads assigned different functional classes;
        # flag this explicitly instead of implying the entire network is perfectly partitioned.
        sum_class_m=sum(g.length for g in class_shapes.values())
        class_overlap_m=max(0,sum_class_m-total_m)
        outputs[code]={"name":name,"car_network_unique_km":round(total_m/1000,3),
          "class_sum_km":round(sum_class_m/1000,3),
          "cross_class_overlap_km":round(class_overlap_m/1000,3),
          "manager_assigned_sum_km":round(sum_assigned_m/1000,3),
          "unmatched_manager_sum_km":round(unmatched_m/1000,3),
          "conflicting_manager_sum_km":round(conflicted_m/1000,3),
          "road_class_by_maintainer":details}
        print("Checked",name,round(total_m/1000,1),"car km, cross-class overlap",round(class_overlap_m/1000,3),flush=True)
    return outputs

def main():
    regions=region_geometries()
    username=os.environ["LASTKAJEN_USERNAME"];password=os.environ["LASTKAJEN_PASSWORD"]
    token=api("/Identity/Login",form={"UserName":username,"Password":password}).get("access_token")
    if not token:raise RuntimeError("Missing access token")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=token)
    if not isinstance(ticket,str):raise ValueError("Invalid download token")
    with tempfile.TemporaryDirectory() as td:
        zpath=Path(td)/"data.zip";amount=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as source,zpath.open("wb") as dest:
            while block:=source.read(1024*1024):
                amount+=len(block)
                if amount>1_500_000_000:raise ValueError("ZIP size limit")
                dest.write(block)
        with zipfile.ZipFile(zpath) as archive:
            members=[m for m in archive.infolist() if m.filename.lower().endswith(".gpkg") and not m.is_dir()]
            if len(members)!=1 or members[0].file_size>8_000_000_000:raise ValueError("Unexpected GeoPackage")
            dbpath=Path(td)/"road.gpkg"
            with archive.open(members[0]) as src,dbpath.open("wb") as dst:
                while block:=src.read(1024*1024):dst.write(block)
            con=sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True)
            try:values=compute(con,regions)
            finally:con.close()
    Path("nvdb_output").mkdir(exist_ok=True)
    (Path("nvdb_output")/"nvdb_road_class_maintainer_qa.json").write_text(
       json.dumps({"status":"qa_only","crs":"EPSG:3006",
          "source":"Trafikverket NVDB Lastkajen Norrbottens län package 10155",
          "method":"Exact geometric intersection of functional car-road class and maintainer centerlines; category union, excludes overlapping conflicting manager assignments.",
          "limitations":"Topological/near-coincident but non-identical linework is unmatched; independent carriageways and cross-class overlap are not automatically normalized. Do not publish until QA.",
          "municipalities":values},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":
    try:main()
    except Exception as exc:print("Road class by maintainer QA failed:",exc,file=sys.stderr);sys.exit(1)
