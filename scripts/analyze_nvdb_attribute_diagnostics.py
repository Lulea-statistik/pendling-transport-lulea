#!/usr/bin/env python3
"""Five-municipality NVDB attribute diagnostics. No raw road geometries are published.
Output is observational: feature-count/length-weighted attributes, NOT traffic totals.
"""
import json, os, sqlite3, sys, tempfile, zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from shapely.geometry import shape
from shapely.ops import transform
from shapely.prepared import prep
from pyproj import Transformer
from build_kommungranser import main as build_boundaries
from inspect_lastkajen_norrbotten import api, BASE, PACKAGE_ID, FILE_NAME
from build_nvdb_five_municipalities import gpkg_geom, quote

TARGETS={"speed":"Hastighetsgrans","adt":"Trafik","gcm_road":"GCM_vagtyp",
         "gcm_crossing":"GCM_passage","cycle_category":"CykelVgsKat"}
# These are accepted only as candidate field names; actual available fields are retained in metadata.
FIELD_HINTS={
    "speed": ("hastighet","hastighetsgrans","hastighetsgrans_varde","speed","skyltad_hastighet"),
    "adt": ("adt_samtliga_fordon","adt_tunga_fordon","matmetod","osakerhet"),
    "gcm_road": ("gcm_vagtyp","vagtyp","typ","kategori"),
    "gcm_crossing": ("passagetyp","trafikanttyp","refug","typ"),
    "cycle_category": ("forbindelsekategori","primar_funktion","kategori","funktion"),
}
def norm(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD",str(text).lower()) if c.isalnum())
def choose_fields(columns,topic):
    hints=[norm(x) for x in FIELD_HINTS[topic]]
    result=[]
    for col in columns:
        n=norm(col)
        if any(h in n for h in hints):
            result.append(col)
    return result[:10]
def region_geometries():
    build_boundaries()
    features=json.loads(Path("boundary_output/municipalities_5.geojson").read_text(encoding="utf-8"))["features"]
    if len(features)!=5:raise ValueError("Expected five municipality polygons")
    convert=Transformer.from_crs("EPSG:4326","EPSG:3006",always_xy=True).transform
    out=[]
    for feature in features:
        geom=transform(convert,shape(feature["geometry"]))
        if not geom.is_valid or geom.is_empty:raise ValueError("Invalid municipality polygon")
        out.append((feature["properties"]["Kommunkod"],feature["properties"]["Kommun"],geom,prep(geom)))
    return out
def bucket(value):
    if value is None:return "(saknas)"
    if isinstance(value,(int,float)):
        if not (-1e12 < float(value) < 1e12):return "(orimligt numeriskt)"
        return str(value)
    return str(value).strip()[:80] or "(tomt)"
def analyze(dbfile, regions):
    con=sqlite3.connect("file:"+str(dbfile)+"?mode=ro",uri=True)
    try:
        layers=con.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns").fetchall()
        output=[]
        for topic,frag in TARGETS.items():
            # Exact layer-name suffix avoids "Trafik" also matching "Vagtrafiknat".
            matches=[x for x in layers if x[0].lower().split("_")[-1]==frag.lower()]
            if len(matches)!=1:
                raise ValueError(f"Expected one {topic} layer, found {len(matches)}: "+str([m[0] for m in matches]))
            table,geocol,srs=matches[0]
            if srs!=3006:raise ValueError("Unexpected CRS: "+str(srs))
            columns=[r[1] for r in con.execute("PRAGMA table_info("+quote(table)+")")]
            fields=choose_fields([c for c in columns if c!=geocol],topic)
            # Metadata includes all field names to allow checking the chosen attributes.
            selected=[geocol]+fields
            statement="SELECT "+",".join(quote(c) for c in selected)+" FROM "+quote(table)
            by_code={code:{"name":name,"intersecting_features":0,"clipped_length_km":0,
                            "fields":{col:defaultdict(lambda:{"features":0,"length_km":0}) for col in fields}}
                     for code,name,*_ in regions}
            null_geom=invalid_geom=0
            for record in con.execute(statement):
                geom=gpkg_geom(record[0])
                if geom is None or geom.is_empty:null_geom+=1;continue
                if not geom.is_valid:invalid_geom+=1;continue
                for code,name,boundary,prepared in regions:
                    if not prepared.intersects(geom):continue
                    clipped=geom.intersection(boundary)
                    length=clipped.length/1000 if "LineString" in clipped.geom_type or clipped.geom_type=="GeometryCollection" else 0
                    b=by_code[code]
                    b["intersecting_features"]+=1;b["clipped_length_km"]+=length
                    for col,val in zip(fields,record[1:]):
                        key=bucket(val);cell=b["fields"][col][key]
                        cell["features"]+=1;cell["length_km"]+=length
            for b in by_code.values():
                b["clipped_length_km"]=round(b["clipped_length_km"],3)
                b["fields"]={field:[{"value":value,"features":v["features"],"clipped_length_km":round(v["length_km"],3)}
                    for value,v in sorted(counts.items(),key=lambda x:(-x[1]["features"],x[0]))[:50]]
                    for field,counts in b["fields"].items()}
            output.append({"topic":topic,"layer":table,"all_columns":columns,"selected_fields":fields,
                           "municipalities":by_code,"null_geometry":null_geom,"invalid_geometry":invalid_geom,
                           "interpretation":"Overlapping and direction-specific objects are NOT deduplicated. ADT is traffic intensity on links, never sum of vehicles."})
            print("Analyzed",topic,table,"fields",fields)
        return output
    finally:con.close()
def main():
    regions=region_geometries()
    user=os.getenv("LASTKAJEN_USERNAME");pw=os.getenv("LASTKAJEN_PASSWORD")
    if not user or not pw:raise RuntimeError("Missing secrets")
    token=api("/Identity/Login",form={"UserName":user,"Password":pw}).get("access_token")
    if not token:raise RuntimeError("Lastkajen authentication failed")
    ticket=api("/file/GetDataPackageDownloadToken?"+urlencode({"id":PACKAGE_ID,"fileName":FILE_NAME}),bearer=token)
    if not isinstance(ticket,str):raise RuntimeError("Unexpected token result")
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"source.zip";total=0
        with urlopen(BASE+"/File/GetDataPackageFile?"+urlencode({"token":ticket}),timeout=180) as src,path.open("wb") as out:
            while part:=src.read(1024*1024):
                total+=len(part)
                if total>1_500_000_000:raise RuntimeError("ZIP size limit exceeded")
                out.write(part)
        with zipfile.ZipFile(path) as archive:
            parts=[x for x in archive.infolist() if x.filename.lower().endswith(".gpkg") and not x.is_dir()]
            if len(parts)!=1:raise ValueError("Expected exactly one GeoPackage")
            if parts[0].file_size>8_000_000_000:raise ValueError("GeoPackage size limit exceeded")
            db=Path(td)/"nvdb.gpkg"
            with archive.open(parts[0]) as src,db.open("wb") as dst:
                while data:=src.read(1024*1024):dst.write(data)
            result=analyze(db,regions)
    Path("nvdb_output").mkdir(exist_ok=True)
    Path("nvdb_output/nvdb_attribute_diagnostics.json").write_text(json.dumps({
        "package_id":PACKAGE_ID,"analysis_crs":"EPSG:3006","status":"diagnostics_only",
        "source":"Trafikverket Lastkajen Norrbottens län",
        "warning":"NOT approved publication indicators. No segment deduplication. ADT field values are not aggregated as flows.",
        "topics":result},ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":
    try:main()
    except Exception as exc:print("NVDB diagnostics failed:",str(exc),file=sys.stderr);sys.exit(1)
