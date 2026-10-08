from __future__ import annotations
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
BASE="https://api.trafa.se/api"

def get(path):
    req=Request(BASE+path,headers={"User-Agent":"pendling-transport-lulea/1.0","Accept":"application/json"})
    with urlopen(req,timeout=120) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8",errors="replace")

def flatten(items):
    out=[]
    def walk(x):
        if isinstance(x,dict):
            out.append({
                "Name":x.get("Name"),"Label":x.get("Label"),"Type":x.get("Type"),
                "ParentName":x.get("ParentName"),"Selected":x.get("Selected"),
                "DataType":x.get("DataType")
            })
            for y in x.get("StructureItems",[]) or []: walk(y)
        elif isinstance(x,list):
            for y in x: walk(y)
    walk(items)
    return out

def main():
    Path("data").mkdir(exist_ok=True)
    queries=["t1004|olyckspl","t1004|olyckspl|kommun","t1004|kommun"]
    out={}
    for q in queries:
        obj=json.loads(get("/structure?query="+quote(q,safe="|:,")))
        flat=flatten(obj.get("StructureItems",[]))
        out[q]=[x for x in flat if x["Selected"] or x["ParentName"] in {"olyckspl","kommun"} or x["Name"]=="kommun"]
    Path("data/trafa_injury_geo_compact.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2)[:20000])
if __name__=="__main__":main()
