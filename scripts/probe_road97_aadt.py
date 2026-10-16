#!/usr/bin/env python3
"""Read-only diagnostic of Trafikverket VTF ArcGIS road 97 AADT geometry."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE="https://vektor.trafikverket.se/gis/rest/services/VTF_MC/Vagtrafikfloden_Mc_gradient/MapServer"
OUT=Path("data/diagnostics/road97_aadt")
# Coarse discovery window, NOT an exact municipal boundary. WGS84 lon/lat.
BOX="21.55,65.54,22.25,65.89"

def get(path, params=None):
    url=BASE+path
    if params: url+="?"+urlencode(params)
    req=Request(url,headers={"User-Agent":"Lulea-statistik/road97-aadt-test"})
    with urlopen(req,timeout=75) as f:
        obj=json.load(f)
    if "error" in obj: raise RuntimeError(str(obj["error"])[:500])
    return obj

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    layers=get("",{"f":"json"}).get("layers",[])
    report={"checked_utc":datetime.now(timezone.utc).isoformat(),"source":BASE,
            "bbox_wgs84":BOX,"road_number":97,"scope_note":"BBox discovery; exact municipal membership and route continuity NOT verified",
            "layers_examined":[],"errors":[]}
    features=[]
    seen=set()
    duplicate_by_layer=Counter()
    geometry_keys=set()
    segment_ids=set()
    for layer in layers:
        if layer.get("subLayerIds"):continue
        lid=layer["id"]
        try:
            meta=get("/"+str(lid),{"f":"json"})
            fields={f["name"] for f in meta.get("fields",[])}
            if not {"VAEG_NUM","AADT_TOT","AVSN_ID"}.issubset(fields):continue
            q={"f":"geojson","where":"VAEG_NUM = 97","geometry":BOX,
               "geometryType":"esriGeometryEnvelope","inSR":"4326","spatialRel":"esriSpatialRelIntersects",
               "outFields":"AVSN_ID,VAEG_NUM,AADT_TOT,AADT_L,AAR,M_METOD","outSR":"4326",
               "returnGeometry":"true","resultRecordCount":1000}
            result=get("/"+str(lid)+"/query",q)
            arr=result.get("features",[])
            report["layers_examined"].append({"id":lid,"name":layer.get("name"),"count":len(arr)})
            for feat in arr:
                a=feat.get("properties") or {}
                key=(a.get("AVSN_ID"),a.get("AAR"),a.get("AADT_TOT"),a.get("AADT_L"))
                if key in seen:
                    duplicate_by_layer[str(lid)]+=1
                    continue
                seen.add(key)
                segment_ids.add(str(a.get('AVSN_ID')))
                geometry_keys.add(json.dumps(feat.get('geometry'),sort_keys=True))
                a["source_layer_id"]=lid
                features.append(feat)
        except Exception as exc:
            report["errors"].append({"layer_id":lid,"reason":str(exc)[:300]})
    report["candidate_segments"]=len(features)
    report["duplicates_removed_by_layer"]=dict(duplicate_by_layer)
    report["unique_segment_ids"]=len(segment_ids)
    report["unique_geometries"]=len(geometry_keys)
    report["missing_geometry"]=sum(not f.get("geometry") for f in features)
    report["missing_fields"]={field:sum(f.get("properties",{}).get(field) is None for f in features) for field in ("AVSN_ID","AADT_TOT","AADT_L","AAR","M_METOD")}
    segment_counts=Counter(str(f.get("properties",{}).get("AVSN_ID")) for f in features)
    report["segments_with_multiple_records"]=sum(n>1 for n in segment_counts.values())
    report["measurement_years"]=dict(Counter(str(f.get("properties",{}).get("AAR")) for f in features))
    report["result_warning"]="Results are geographic road-97 candidates only, not validated Lulea/Boden municipal clipping. Layer duplication and distinct same-value segments need review."
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (OUT/"candidates.geojson").write_text(json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report["layers_examined"]: raise RuntimeError("No suitable AADT layers found; review report")
if __name__=="__main__":main()

# Initial diagnostic run.
