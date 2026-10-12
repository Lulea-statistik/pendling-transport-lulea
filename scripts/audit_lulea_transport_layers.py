#!/usr/bin/env python3
"""Audit targeted municipal ArcGIS REST layers (metadata, record counts, limited attribute samples).
No local traffic measurement layer queries; no Storheden measurements.
"""
import json,urllib.request,urllib.parse,urllib.error,datetime
from pathlib import Path
BASE="https://kartportal.lulea.se/server/rest/services/samhalle_och_gator/MapServer"
LAYERS={"vaghallare":35,"farligt_gods_rekommenderad":38,"farligt_gods_forbud":39,
 "parkering_uppstallning_54":54,"parkering_uppstallning_56":56,"parkering_5":5,
 "parkering_6":6,"parkering_7":7,"laddplats":2,"parkeringsforbud":58,"korforbud":59}
def fetch(url,params=None):
    if params:url+="?"+urllib.parse.urlencode(params)
    try:
        request=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"Lulea-statistik-transport-layer-audit"})
        with urllib.request.urlopen(request,timeout=45) as resp:
            content=resp.read(500000)
        result=json.loads(content)
        if "error" in result:return {"ok":False,"error":result["error"]}
        return {"ok":True,"data":result}
    except Exception as exc:return {"ok":False,"error":str(exc)[:260]}
def main():
    out={"source":BASE,"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"diagnostic_only","notes":"All samples limited to 2 public objects per layer. No private tokens; never treats general parking as legal heavy truck space.","layers":{}}
    for key,number in LAYERS.items():
        url=BASE+"/"+str(number)
        meta=fetch(url,{"f":"pjson"})
        result={"id":number,"url":url,"metadata_ok":meta["ok"]}
        if not meta["ok"]:
            result["metadata_error"]=meta["error"];out["layers"][key]=result;continue
        item=meta["data"]
        result.update({"name":item.get("name"),"type":item.get("type"),
            "parentLayer":item.get("parentLayer"),"geometryType":item.get("geometryType"),
            "capabilities":item.get("capabilities"),"advancedQueryCapabilities":item.get("advancedQueryCapabilities"),
            "fields":[{"name":f.get("name"),"alias":f.get("alias"),"type":f.get("type")} for f in item.get("fields",[])],
            "subLayers":item.get("subLayers"),"maxRecordCount":item.get("maxRecordCount")})
        if "Query" in str(item.get("capabilities","")):
            count=fetch(url+"/query",{"f":"json","where":"1=1","returnCountOnly":"true"})
            result["count"]=count.get("data",{}).get("count") if count["ok"] else None
            if not count["ok"]:result["count_error"]=count["error"]
            sample=fetch(url+"/query",{"f":"json","where":"1=1","returnGeometry":"false","outFields":"*","resultRecordCount":"2"})
            if sample["ok"]:result["attribute_samples"]=[f.get("attributes",{}) for f in sample["data"].get("features",[])][:2]
            else:result["sample_error"]=sample["error"]
        out["layers"][key]=result
        print(number,key,"meta",result["metadata_ok"],"count",result.get("count"),flush=True)
    target=Path("nvdb_output/lulea_transport_layer_attribute_audit.json");target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
if __name__=="__main__":main()
