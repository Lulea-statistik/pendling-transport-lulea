#!/usr/bin/env python3
"""NVDB road-width and lane-count by functional road class, same-centerline only.
Diagnostic export; unknown and overlapping classifications are reported explicitly.
"""
import json,os,sqlite3,sys,tempfile,zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.ops import unary_union
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME
from analyze_nvdb_attribute_diagnostics import region_geometries
from analyze_nvdb_road_class_maintainer import read_lines

def width_band(value):
    try:
        v=float(str(value).replace(",","."))
        if not 1<=v<=50:return "(okänt)"
        if v<4:return "<4 m"
        if v<6:return "4–<6 m"
        if v<8:return "6–<8 m"
        if v<10:return "8–<10 m"
        return "≥10 m"
    except (TypeError,ValueError):return "(okänt)"

def lane_band(value):
    try:
        n=int(float(value))
        return str(n) if 1<=n<=8 else "(okänt)"
    except (TypeError,ValueError):return "(okänt)"

def analyze(con,regions):
    klass=read_lines(con,"FunkVagklass","Klass",regions)
    width=read_lines(con,"Vagbredd","Bredd",regions)
    lanes=read_lines(con,"Antal_korfalt2","Korfaltsantal",regions)
    output={}
    for code,name,*_ in regions:
        classes={k:g for k,g in klass[code].items() if k.isdigit() and 0<=int(k)<=9}
        road_union=unary_union(list(classes.values()))
        municipality={"name":name,"car_network_km":round(road_union.length/1000,3),"variables":{}}
        for key,raw,group in (("width",width[code],width_band),("lanes",lanes[code],lane_band)):
            bands={}
            for value,geometry in raw.items():
                category=group(value)
                bands.setdefault(category,[]).append(geometry)
            bands={k:unary_union(v) for k,v in bands.items()}
            class_output={}
            for klass_id,road in classes.items():
                intersections={k:road.intersection(g) for k,g in bands.items()}
                covered=unary_union(list(intersections.values())) if intersections else None
                covered_m=covered.length if covered else 0.0
                other={k:g for k,g in intersections.items() if k!="(okänt)" and g.length>0}
                good=unary_union(list(other.values())) if other else None
                good_m=good.length if good else 0.0
                overlap_m=max(0,sum(g.length for g in intersections.values())-covered_m)
                observed=sum(g.length for g in intersections.values())
                counts={k:round(g.length/1000,3) for k,g in intersections.items() if g.length>0}
                class_output[klass_id]={"class_km":round(road.length/1000,3),"bands_km":counts,
                    "covered_any_km":round(covered_m/1000,3),
                    "known_km":round(good_m/1000,3),
                    "no_attribute_km":round(max(0,road.length-covered_m)/1000,3),
                    "multiple_attribute_km":round(overlap_m/1000,3),
                    "classification_overlap_km":round(max(0,observed-covered_m)/1000,3)}
            municipality["variables"][key]=class_output
        output[code]=municipality
        print(name,"class width + lanes measured",flush=True)
    return output

def main():
    regions=region_geometries()
    user=os.environ["LASTKAJEN_USERNAME"];pw=os.environ["LASTKAJEN_PASSWORD"]
    bearer=api("/Identity/Login",form={"UserName":user,"Password":pw}).get("access_token")
    if not bearer:raise RuntimeError("Lastkajen login failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    if not isinstance(ticket,str):raise ValueError("Invalid ticket")
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/"data.zip";size=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as response,archive.open("wb") as dest:
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>1_500_000_000:raise ValueError("ZIP too large")
                dest.write(chunk)
        with zipfile.ZipFile(archive) as z:
            gpkg=[x for x in z.infolist() if x.filename.lower().endswith(".gpkg") and not x.is_dir()]
            if len(gpkg)!=1 or gpkg[0].file_size>8_000_000_000:raise ValueError("Unexpected GeoPackage")
            db=Path(td)/"source.gpkg"
            with z.open(gpkg[0]) as source,db.open("wb") as dest:
                while chunk:=source.read(1024*1024):dest.write(chunk)
            con=sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True)
            try:result=analyze(con,regions)
            finally:con.close()
    Path("nvdb_output").mkdir(exist_ok=True)
    Path("nvdb_output/nvdb_road_width_lanes_qa.json").write_text(json.dumps({
        "status":"qa_only","source":"NVDB Lastkajen Norrbotten package 10155",
        "method":"Exact line overlap of FunkVagklass / Vagbredd / Antal_korfalt2 in EPSG:3006",
        "limits":"Breddtolkning behöver verifieras mot datadefinition. Parallella körbanor och ofullständig täckning måste kontrolleras. Ingen imputering från närmaste väg.",
        "municipalities":result},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":
    try:main()
    except Exception as ex:print("NVDB road standard analysis failed:",ex,file=sys.stderr);sys.exit(1)
