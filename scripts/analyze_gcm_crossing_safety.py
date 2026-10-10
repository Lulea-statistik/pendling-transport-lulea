#!/usr/bin/env python3
"""Exploratory GCM crossing x posted speed analysis. No safety ratings or coordinates published."""
import json, os, sqlite3, sys, tempfile, zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.strtree import STRtree
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME
from analyze_nvdb_attribute_diagnostics import region_geometries
from build_nvdb_five_municipalities import gpkg_geom,quote

MAX_DISTANCE_M=12.0
def geom_column(con,table):
    row=con.execute("SELECT column_name,srs_id FROM gpkg_geometry_columns WHERE table_name=?",(table,)).fetchone()
    if not row or row[1]!=3006:raise ValueError("Unexpected missing layer or CRS: "+table)
    return row[0]
def table_for(con,suffix):
    layers=[r[0] for r in con.execute("SELECT table_name FROM gpkg_geometry_columns") if r[0].lower().endswith("_"+suffix.lower())]
    if len(layers)!=1:raise ValueError("Ambiguous layer "+suffix+": "+str(layers))
    return layers[0]
def analyze(con,regions):
    speed_table=table_for(con,"Hastighetsgrans");cross_table=table_for(con,"GCM_passage")
    sg=geom_column(con,speed_table);cg=geom_column(con,cross_table)
    speed=[]
    sql="SELECT "+quote(sg)+","+quote("Hogsta_tillatna_hastighet")+" FROM "+quote(speed_table)
    for blob,value in con.execute(sql):
        geom=gpkg_geom(blob)
        try:v=float(value)
        except (ValueError,TypeError):continue
        if geom is not None and not geom.is_empty and geom.is_valid and 5<=v<=140:speed.append((geom,int(v)))
    if not speed:raise ValueError("No speed records")
    tree=STRtree([x[0] for x in speed])
    columns=[r[1] for r in con.execute("PRAGMA table_info("+quote(cross_table)+")")]
    attr=[x for x in ("Passagetyp","Trafikanttyp","Refugpassage") if x in columns]
    if "Passagetyp" not in attr:raise ValueError("Missing passage classification")
    statement="SELECT "+",".join(quote(x) for x in [cg]+attr)+" FROM "+quote(cross_table)
    out={code:{"name":name,"passages":0,"matches":0,"unmatched":0,"ambiguous":0,"speed_classes":Counter(),"speed_by_type":{},"at_grade_by_refuge_and_speed":{},"at_grade_by_traveler_and_speed":{},"attribute_columns":attr} for code,name,*_ in regions}
    for row in con.execute(statement):
        geom=gpkg_geom(row[0])
        if geom is None or geom.is_empty or not geom.is_valid:continue
        attrs=dict(zip(attr,row[1:]))
        for code,name,boundary,prepared in regions:
            if not prepared.intersects(geom):continue
            bucket=out[code];bucket["passages"]+=1
            nearest=tree.query(geom.buffer(MAX_DISTANCE_M))
            distances=[]
            for idx in nearest:
                road,limit=speed[int(idx)]
                delta=geom.distance(road)
                if delta<=MAX_DISTANCE_M:distances.append((delta,limit))
            if not distances:
                bucket["unmatched"]+=1;continue
            best=min(x[0] for x in distances)
            # Do not choose one of several distinct speeds at effectively equal proximity.
            candidates={v for dist,v in distances if dist<=best+1.0}
            if len(candidates)!=1:
                bucket["ambiguous"]+=1;continue
            limit=candidates.pop();key=str(limit)
            bucket["matches"]+=1;bucket["speed_classes"][key]+=1
            p=str(attrs["Passagetyp"]) if attrs["Passagetyp"] is not None else "(saknas)"
            bytype=bucket["speed_by_type"].setdefault(p,Counter())
            bytype[key]+=1
            if " i plan" in p.lower() and "planskild" not in p.lower():
                refuge=str(attrs.get("Refugpassage")) if attrs.get("Refugpassage") is not None else "(saknas)"
                traveler=str(attrs.get("Trafikanttyp")) if attrs.get("Trafikanttyp") is not None else "(saknas)"
                bucket["at_grade_by_refuge_and_speed"].setdefault(refuge,Counter())[key]+=1
                bucket["at_grade_by_traveler_and_speed"].setdefault(traveler,Counter())[key]+=1
    for item in out.values():
        item["speed_classes"]=dict(item["speed_classes"])
        item["speed_by_type"]={k:dict(v) for k,v in item["speed_by_type"].items()}
        item["at_grade_by_refuge_and_speed"]={k:dict(v) for k,v in item["at_grade_by_refuge_and_speed"].items()}
        item["at_grade_by_traveler_and_speed"]={k:dict(v) for k,v in item["at_grade_by_traveler_and_speed"].items()}
        if item["matches"]!=sum(sum(v.values()) for v in item["speed_by_type"].values()):
            raise ValueError("Passage type by speed does not balance")
        nplan=sum(sum(v.values()) for k,v in item["speed_by_type"].items() if " i plan" in k.lower() and "planskild" not in k.lower())
        if nplan and not item["at_grade_by_refuge_and_speed"]:
            raise ValueError("At-grade refuge classification is unexpectedly empty")
        if "Refugpassage" in attr and nplan!=sum(sum(v.values()) for v in item["at_grade_by_refuge_and_speed"].values()):
            raise ValueError("Refuge at-grade totals do not balance")
        if "Trafikanttyp" in attr and nplan!=sum(sum(v.values()) for v in item["at_grade_by_traveler_and_speed"].values()):
            raise ValueError("Traveler type at-grade totals do not balance")
        if item["passages"]!=item["matches"]+item["unmatched"]+item["ambiguous"]:
            raise ValueError("Passage total mismatch")
    return out
def main():
    regions=region_geometries()
    user=os.environ["LASTKAJEN_USERNAME"];password=os.environ["LASTKAJEN_PASSWORD"]
    access=api("/Identity/Login",form={"UserName":user,"Password":password}).get("access_token")
    if not access:raise RuntimeError("Lastkajen login failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=access)
    if not isinstance(ticket,str):raise ValueError("Unexpected ticket")
    with tempfile.TemporaryDirectory() as td:
        zippath=Path(td)/"source.zip"
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as stream,zippath.open("wb") as out:
            size=0
            while chunk:=stream.read(1024*1024):
                size+=len(chunk)
                if size>1_500_000_000:raise ValueError("ZIP too large")
                out.write(chunk)
        with zipfile.ZipFile(zippath) as archive:
            members=[m for m in archive.infolist() if m.filename.lower().endswith(".gpkg") and not m.is_dir()]
            if len(members)!=1 or members[0].file_size>8_000_000_000:raise ValueError("Unexpected GeoPackage")
            dbpath=Path(td)/"source.gpkg"
            with archive.open(members[0]) as a,dbpath.open("wb") as b:
                while chunk:=a.read(1024*1024):b.write(chunk)
            con=sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True)
            try:result=analyze(con,regions)
            finally:con.close()
    Path("nvdb_output").mkdir(exist_ok=True)
    Path("nvdb_output/gcm_crossing_speed_qa.json").write_text(json.dumps({
      "status":"qa_only","source":"Trafikverket NVDB Lastkajen Norrbotten",
      "method":"Nearest posted-speed geometry within 12m; ties between speed classes within 1m excluded; no causal safety classification.",
      "limits":"Refuges and traveler types are source attributes, not safety grades. This proximity join does not prove which physical carriageway is crossed; bridges and tunnels can overlap in 2D. Traffic volume, accident history and legal priority not used.",
      "municipalities":result},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Computed GCM crossing speed proximity QA for",len(result),"municipalities")
if __name__=="__main__":
    try:main()
    except Exception as exc:print("GCM safety QA failed:",str(exc),file=sys.stderr);sys.exit(1)
