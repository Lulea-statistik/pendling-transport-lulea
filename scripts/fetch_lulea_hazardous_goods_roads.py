#!/usr/bin/env python3
"""Export and QA public Lulea hazardous-goods road geometries; exclude traffic measurements."""
import json,urllib.request,urllib.parse,datetime,math
from pathlib import Path
BASE="https://kartportal.lulea.se/server/rest/services/samhalle_och_gator/MapServer"
LAYER_IDS={"recommended":38,"restricted":39}
def request(url,params):
    u=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers={"User-Agent":"Lulea-statistik-public-transport-geometry-QA","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=75) as r:data=json.load(r)
    if "error" in data:raise ValueError(str(data["error"]))
    return data
def main():
    features=[];report={}
    for name,layer_id in LAYER_IDS.items():
        url=BASE+"/"+str(layer_id)
        meta=request(url,{"f":"json"})
        if meta.get("geometryType")!="esriGeometryPolyline":raise ValueError("Not a polyline layer "+name)
        ids=request(url+"/query",{"f":"json","where":"1=1","returnIdsOnly":"true"}).get("objectIds",[])
        if len(ids)!=len(set(ids)):raise ValueError("Duplicate object IDs")
        count=request(url+"/query",{"f":"json","where":"1=1","returnCountOnly":"true"})["count"]
        if len(ids)!=count:raise ValueError("Count mismatch "+name)
        if count>3000:raise ValueError("Unexpectedly many source lines")
        observed=set();npaths=0;vertices=0;invalid=0;class_counts={}
        for ix in range(0,len(ids),100):
            batch=ids[ix:ix+100]
            result=request(url+"/query",{"f":"json","objectIds":",".join(map(str,batch)),
                       "outFields":"*","returnGeometry":"true","outSR":"4326"})
            for f in result.get("features",[]):
                attrs=f.get("attributes") or {}; oid=attrs.get("OBJECTID")
                if oid not in batch or oid in observed:raise ValueError("Unexpected object id")
                observed.add(oid)
                paths=(f.get("geometry") or {}).get("paths") or []
                good=[]
                for path in paths:
                    if len(path)<2:invalid+=1;continue
                    if not all(len(p)>=2 and all(math.isfinite(float(v)) for v in p[:2]) and -180<=p[0]<=180 and -90<=p[1]<=90 for p in path):
                        invalid+=1;continue
                    good.append([[float(p[0]),float(p[1])] for p in path]);vertices+=len(path)
                if not good:invalid+=1;continue
                npaths+=len(good)
                label=str(attrs.get("REKOMMENDATION") or attrs.get("DIRECTION") or "Ej klassificerad")
                class_counts[label]=class_counts.get(label,0)+1
                features.append({"type":"Feature","geometry":{"type":"MultiLineString","coordinates":good},
                    "properties":{"layer":name,"source_layer_id":layer_id,"objectid":oid,
                       "classification":label,"valid_from":attrs.get("GILTIG_FROM") or attrs.get("VALID_FROM"),
                       "valid_to":attrs.get("GILTIG_TOM") or attrs.get("VALID_TO")}})
        if len(observed)!=count:raise ValueError("Missing IDs "+name)
        if invalid:raise ValueError("Unexpected or invalid geometry "+str(invalid))
        report[name]={"layer_id":layer_id,"objects":count,"downloaded":len(observed),"paths":npaths,"vertices":vertices,"classes":class_counts}
    out=Path("docs/data");out.mkdir(parents=True,exist_ok=True)
    (out/"lulea-hazardous-goods-roads.geojson").write_text(json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (out/"lulea-hazardous-goods-roads-qa.json").write_text(json.dumps({"status":"geometry_verified_not_legally_verified","checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source":BASE,"crs":"EPSG:4326","notes":"Public geometries with source classifications. Not a route planner; check current traffic regulations and temporal validity. No Storheden traffic measurements used.","layers":report},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()
