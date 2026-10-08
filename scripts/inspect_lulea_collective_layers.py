# ArcGIS kollektivtrafik-inspektion
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE="https://s-gis07.lulea.se/arcgis/rest/services/ext/kollektivtrafik/MapServer"

def get_json(url, params=None):
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0","Accept":"application/json"})
    with urlopen(req,timeout=120) as r:
        return json.loads(r.read().decode(r.headers.get_content_charset() or "utf-8",errors="replace"))

def main():
    service=get_json(BASE,{"f":"json"})
    out={"service":service,"layers":[]}
    for lyr in service.get("layers",[]):
        lid=lyr["id"]
        meta=get_json(f"{BASE}/{lid}",{"f":"json"})
        q=get_json(f"{BASE}/{lid}/query",{
            "where":"1=1",
            "outFields":"*",
            "returnGeometry":"true",
            "outSR":"4326",
            "f":"geojson"
        })
        out["layers"].append({
            "id":lid,
            "name":lyr.get("name"),
            "geometryType":meta.get("geometryType"),
            "displayField":meta.get("displayField"),
            "fields":[
                {"name":f.get("name"),"alias":f.get("alias"),"type":f.get("type")}
                for f in meta.get("fields",[])
            ],
            "count":len(q.get("features",[])),
            "sample":q.get("features",[])[:3],
        })
    Path("data").mkdir(exist_ok=True)
    Path("data/lulea_collective_layers.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps([
        {"id":x["id"],"name":x["name"],"geometryType":x["geometryType"],"count":x["count"],
         "fields":[f["name"] for f in x["fields"]]}
        for x in out["layers"]
    ],ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
