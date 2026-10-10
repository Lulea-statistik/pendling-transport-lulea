#!/usr/bin/env python3
"""Build five municipality boundaries from SCB RegSO 2025. Fail closed on ambiguous input."""
import json
import sys
import requests
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from pyproj import Transformer

CODES={"2580":"Luleå","2582":"Boden","2581":"Piteå","2514":"Kalix","2560":"Älvsbyn"}
URL="https://geodata.scb.se/geoserver/stat/wfs"
params={"service":"WFS","version":"1.1.0","request":"GetFeature",
        "typeName":"stat:RegSO_2025","outputFormat":"application/json","srsName":"EPSG:3006"}
def main():
    r=requests.get(URL,params=params,timeout=180);r.raise_for_status()
    data=r.json()
    # Reject unexpected response CRS; WFS 1.1 services can have axis-order pitfalls.
    declared=json.dumps(data.get("crs",{})).upper()
    if declared and "3006" not in declared:
        raise ValueError("Unexpected GeoJSON CRS declaration: "+declared[:200])
    features=data.get("features",[])
    if not features: raise ValueError("No RegSO 2025 features returned")
    # Only use a four-digit municipality code field, never guess from feature ordering.
    fields=set().union(*(f.get("properties",{}).keys() for f in features[:10]))
    candidates=[k for k in fields if k.lower() in ("kommunkod","kommun_kod","kommun","knkod","kn_kod","kommunkod_2025")]
    scored=[]
    for key in candidates:
        vals=[str(f.get("properties",{}).get(key,"")).strip() for f in features]
        count=sum(v in CODES for v in vals)
        if count: scored.append((count,key))
    if not scored: raise ValueError("No verified municipality-code column; available columns: "+", ".join(sorted(fields)))
    scored.sort(reverse=True)
    if len(scored)>1 and scored[0][0]==scored[1][0]: raise ValueError("Ambiguous code fields: "+str(scored))
    code_field=scored[0][1]
    group={code:[] for code in CODES}
    for f in features:
        code=str(f.get("properties",{}).get(code_field,"")).strip()
        if code in group:
            geom=shape(f["geometry"])
            if geom.is_empty or not geom.is_valid: raise ValueError("Invalid source geometry for "+code)
            minx,miny,maxx,maxy=geom.bounds
            if not (100000<minx<1000000 and 6000000<miny<8000000 and 100000<maxx<1000000 and 6000000<maxy<8000000):
                raise ValueError("Coordinates are not plausible EPSG:3006 for "+code)
            group[code].append(geom)
    missing=[code for code,items in group.items() if not items]
    if missing: raise ValueError("Missing municipalities: "+", ".join(missing))
    fc={"type":"FeatureCollection","features":[]}
    report={"source":"SCB WFS RegSO 2025","source_url":r.url,"source_crs":"EPSG:3006","analysis_crs":"EPSG:3006","code_field":code_field,"municipalities":[]}
    to4326=Transformer.from_crs("EPSG:3006","EPSG:4326",always_xy=True).transform
    for code,name in CODES.items():
        geom=unary_union(group[code])
        if geom.is_empty or not geom.is_valid: raise ValueError("Invalid dissolved geometry: "+name)
        report["municipalities"].append({"code":code,"name":name,"regso_parts":len(group[code]),"area_km2":round(geom.area/1000000,2),"valid":True})
        fc["features"].append({"type":"Feature","properties":{"Kommunkod":code,"Kommun":name},"geometry":mapping(transform(to4326,geom))})
    out=Path("boundary_output");out.mkdir(exist_ok=True)
    (out/"municipalities_5.geojson").write_text(json.dumps(fc,ensure_ascii=False),encoding="utf-8")
    (out/"boundary_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Validated five SCB RegSO 2025 municipality boundaries; source geometry EPSG:3006; GeoJSON EPSG:4326")
if __name__=="__main__":
    try: main()
    except Exception as e:
        print("Boundary verification failed:",str(e),file=sys.stderr)
        sys.exit(1)
