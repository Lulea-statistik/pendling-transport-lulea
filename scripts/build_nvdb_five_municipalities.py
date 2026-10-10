#!/usr/bin/env python3
"""NVDB five-municipality geometry clipping and QA; artifact only, no raw data."""
import json, os, sqlite3, sys, tempfile, zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.geometry import shape
from shapely.ops import transform
from shapely.prepared import prep
from shapely import wkb
from pyproj import Transformer
from build_kommungranser import main as build_boundaries
from inspect_lastkajen_norrbotten import api, BASE, PACKAGE_ID, FILE_NAME

# Target only specifically checked NVDB topics. Fields and geometry type are discovered.
TOPICS={
 "Trafik":"Trafik",
 "Hastighetsgrans":"Hastighetsgrans",
 "ForbjudenFardriktning":"ForbjudenFardriktning",
 "GCM_passage":"GCM_passage",
 "CykelVgsKat":"CykelVgsKat",
 "GCM_vagtyp":"GCM_vagtyp",
 "Farthinder":"Farthinder",
 "FunkVagklass":"FunkVagklass",
 "Vagbredd":"Vagbredd",
 "Vagtrafiknat":"Vagtrafiknat",
}
MAX_ZIP_BYTES=1_500_000_000
def quote(s):return '"'+s.replace('"','""')+'"'
def gpkg_geom(blob):
    if not blob:return None
    if bytes(blob[:2])!=b"GP":raise ValueError("Not a GeoPackage geometry")
    flags=blob[3]
    if flags & 0x10:return None  # Empty geometry
    envelope=(flags>>1)&7
    skip={0:0,1:32,2:48,3:48,4:64}
    if envelope not in skip:raise ValueError("Unexpected GPKG envelope type")
    return wkb.loads(bytes(blob[8+skip[envelope]:]))
def boundaries():
    build_boundaries()
    features=json.loads(Path("boundary_output/municipalities_5.geojson").read_text(encoding="utf-8"))["features"]
    if len(features)!=5:raise ValueError("Expected exactly five validated municipalities")
    to3006=Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform
    out=[]
    for f in features:
        polygon=transform(to3006,shape(f["geometry"]))
        if not polygon.is_valid or polygon.is_empty:raise ValueError("Invalid municipality geometry")
        out.append((f["properties"]["Kommunkod"],f["properties"]["Kommun"],polygon,prep(polygon)))
    return out
def summarize_database(dbfile,regions):
    db=sqlite3.connect("file:"+str(dbfile)+"?mode=ro",uri=True)
    try:
        layers=db.execute("SELECT table_name,column_name,geometry_type_name,srs_id FROM gpkg_geometry_columns").fetchall()
        chosen=[x for x in layers if any(t.lower() in x[0].lower() for t in TOPICS)]
        if not chosen:raise ValueError("No target NVDB layers")
        results=[]
        for table,geocol,geomtype,srs in chosen:
            if srs!=3006:raise ValueError(f"Unexpected CRS in {table}: {srs}")
            stats={code:{"municipality":name,"objects_intersecting":0,"clipped_line_km":0.0,
                         "points_intersecting":0,"invalid_geometries":0} for code,name,*_ in regions}
            issues={"null_or_empty":0,"invalid":0,"unsupported_geometry":0}
            rows=0
            # Read only geometry, not whole feature attributes, in bounded batches.
            cur=db.execute("SELECT "+quote(geocol)+" FROM "+quote(table))
            while True:
                batch=cur.fetchmany(512)
                if not batch:break
                for (blob,) in batch:
                    rows+=1
                    geom=gpkg_geom(blob)
                    if geom is None or geom.is_empty:issues["null_or_empty"]+=1;continue
                    if not geom.is_valid:issues["invalid"]+=1;continue
                    for code,name,boundary,prepared in regions:
                        if not prepared.intersects(geom):continue
                        stats[code]["objects_intersecting"]+=1
                        clipped=geom.intersection(boundary)
                        if "LineString" in geom.geom_type or geom.geom_type=="GeometryCollection":
                            stats[code]["clipped_line_km"]+=clipped.length/1000
                        elif "Point" in geom.geom_type:
                            stats[code]["points_intersecting"]+=1
                        else:issues["unsupported_geometry"]+=1
            for x in stats.values():x["clipped_line_km"]=round(x["clipped_line_km"],3)
            results.append({"layer":table,"geometry_type":geomtype,"source_rows":rows,
                            "by_municipality":stats,"issues":issues,
                            "warning":"Counts are feature intersections, not deduplicated road kilometres. No ADT aggregation."})
            print("Processed",table,rows,"features")
        return results
    finally:db.close()
def main():
    regions=boundaries()
    user=os.getenv("LASTKAJEN_USERNAME");password=os.getenv("LASTKAJEN_PASSWORD")
    if not user or not password:raise RuntimeError("Missing Lastkajen secrets")
    bearer=api("/Identity/Login",form={"UserName":user,"Password":password}).get("access_token")
    if not bearer:raise RuntimeError("Login did not return access token")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=bearer)
    if not isinstance(ticket,str):raise RuntimeError("Unexpected download token")
    with tempfile.TemporaryDirectory() as td:
        arch=Path(td)/"nvdb.zip"
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as src, arch.open("wb") as dst:
            total=0
            while block:=src.read(1024*1024):
                total+=len(block)
                if total>MAX_ZIP_BYTES:raise RuntimeError("Downloaded ZIP larger than limit")
                dst.write(block)
        with zipfile.ZipFile(arch) as z:
            gpkg=[x for x in z.infolist() if x.filename.lower().endswith(".gpkg") and not x.is_dir()]
            if len(gpkg)!=1:raise RuntimeError("Expected one GPKG in archive")
            if gpkg[0].file_size>8_000_000_000:raise RuntimeError("Uncompressed file too large")
            path=Path(td)/"source.gpkg"
            with z.open(gpkg[0]) as src,path.open("wb") as dst:
                while block:=src.read(1024*1024):dst.write(block)
            result=summarize_database(path,regions)
    output=Path("nvdb_output");output.mkdir(exist_ok=True)
    (output/"municipality_nvdb_qa.json").write_text(
        json.dumps({"source":"NVDB Lastkajen Norrbotten county 10155","municipalities":[r[0] for r in regions],
                    "analysis_crs":"EPSG:3006","layers":result,
                    "limitations":"Exploratory intersection counts and sum of clipped feature lengths; not network-deduplicated. Not published as traffic indicators."},
                   indent=2,ensure_ascii=False),encoding="utf-8")
    print("QA artifact created; no raw NVDB geometries exported")
if __name__=="__main__":
    try:main()
    except Exception as e:print("NVDB clipping failed:",str(e),file=sys.stderr);sys.exit(1)
