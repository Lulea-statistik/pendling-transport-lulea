#!/usr/bin/env python3
"""Municipal road structure statistics; diagnostic only until network duplicate QA."""
import json,os,sqlite3,sys,tempfile,zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.ops import unary_union
from inspect_lastkajen_norrbotten import api,BASE,PACKAGE_ID,FILE_NAME
from analyze_nvdb_attribute_diagnostics import region_geometries
from build_nvdb_five_municipalities import gpkg_geom,quote

LAYERS={"road_class":("FunkVagklass","Klass"),"maintainer":("Vaghallare","Vaghallartyp"),"road_network":("Vagtrafiknat","Nattyp")}
def clean(value,topic):
    if value is None:return "(saknas)"
    v=str(value).strip()
    if topic=="road_class":
        try:
            n=int(v)
            return str(n) if str(n)==v and 0<=n<=9 else "(okänd klass)"
        except ValueError:return "(okänd klass)"
    if topic=="maintainer":return v.lower() if v.lower() in ("statlig","kommunal","enskild") else "(okänd väghållare)"
    return v.lower() or "(saknas)"
def analyze(con,regions):
    tables={t:(geo,srs) for t,geo,srs in con.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns")}
    result={}
    for topic,(suffix,field) in LAYERS.items():
        matches=[k for k in tables if k.lower().endswith("_"+suffix.lower())]
        if len(matches)!=1:raise ValueError("Expected one "+suffix+" layer: "+str(matches))
        table=matches[0];geom,srs=tables[table]
        if srs!=3006:raise ValueError("Unexpected CRS "+table)
        cols=[r[1] for r in con.execute("PRAGMA table_info("+quote(table)+")")]
        if field not in cols:raise ValueError("Missing "+field+" in "+table)
        by_muni={code:{"name":name,"objects":0,"clipped_feature_km":0.0,"classifications":defaultdict(lambda:{"objects":0,"clipped_feature_km":0.0}),"raw_geometries":defaultdict(list)} for code,name,*_ in regions}
        for blob,value in con.execute("SELECT "+quote(geom)+","+quote(field)+" FROM "+quote(table)):
            road=gpkg_geom(blob)
            if road is None or road.is_empty or not road.is_valid or road.geom_type not in ("LineString","MultiLineString"):continue
            classification=clean(value,topic)
            for code,name,polygon,prepared in regions:
                if not prepared.intersects(road):continue
                clipped=road.intersection(polygon)
                if clipped.is_empty or clipped.length<=0:continue
                length=clipped.length/1000
                cell=by_muni[code];cell["objects"]+=1;cell["clipped_feature_km"]+=length
                cat=cell["classifications"][classification]
                cat["objects"]+=1;cat["clipped_feature_km"]+=length
                cell["raw_geometries"][classification].append(clipped)
        for municipality in by_muni.values():
            union_classes=[]
            for key,parts in municipality["raw_geometries"].items():
                unioned=unary_union(parts)
                municipality["classifications"][key]["unique_within_category_km"]=round(unioned.length/1000,3)
                union_classes.append(unioned)
            # Unique geometry across all classes prevents summing duplicated/overlapping class objects.
            municipality["unique_across_categories_km"]=round(unary_union(union_classes).length/1000,3) if union_classes else 0
            municipality["clipped_feature_km"]=round(municipality["clipped_feature_km"],3)
            municipality["classifications"]=dict(municipality["classifications"])
            for c in municipality["classifications"].values():c["clipped_feature_km"]=round(c["clipped_feature_km"],3)
            del municipality["raw_geometries"]
        result[topic]={"layer":table,"field":field,"municipalities":by_muni}
        print(topic,"matched",table,flush=True)
    return result
def main():
    regions=region_geometries()
    username=os.environ["LASTKAJEN_USERNAME"];password=os.environ["LASTKAJEN_PASSWORD"]
    bearer=api("/Identity/Login",form={"UserName":username,"Password":password}).get("access_token")
    if not bearer:raise RuntimeError("Authentication failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    if not isinstance(ticket,str):raise ValueError("Unexpected download ticket")
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/"source.zip";size=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as response,archive.open("wb") as output:
            while piece:=response.read(1024*1024):
                size+=len(piece)
                if size>1_500_000_000:raise RuntimeError("Source too large")
                output.write(piece)
        with zipfile.ZipFile(archive) as z:
            members=[v for v in z.infolist() if not v.is_dir() and v.filename.lower().endswith(".gpkg")]
            if len(members)!=1 or members[0].file_size>8_000_000_000:raise ValueError("Expected one GeoPackage under limit")
            dbpath=Path(td)/"roads.gpkg"
            with z.open(members[0]) as source,dbpath.open("wb") as target:
                while piece:=source.read(1024*1024):target.write(piece)
            con=sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True)
            try:result=analyze(con,regions)
            finally:con.close()
    Path("nvdb_output").mkdir(exist_ok=True)
    Path("nvdb_output/nvdb_road_structure_qa.json").write_text(json.dumps({"status":"qa_only","source":"NVDB Norrbottens län Lastkajen package 10155","crs":"EPSG:3006","limitations":"Within-category line union removes exactly coincident linework, but different carriageways, direction, and cross-category overlaps need scrutiny. FA total is not computed by summing category unique lengths without accounting for municipality overlap.","topics":result},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":
    try:main()
    except Exception as ex:print("Road structure failed:",ex,file=sys.stderr);sys.exit(1)
