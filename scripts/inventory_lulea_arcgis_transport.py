#!/usr/bin/env python3
"""Probe Lulea public ArcGIS catalog metadata, no bulk downloads and no auth bypass."""
import json,urllib.request,urllib.error,datetime
from pathlib import Path
BASE="https://kartportal.lulea.se/server/rest/services"
TARGETS=("farligt gods","väghållare","parkering","lastzon","uppställ","trafik")
def get(url):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Lulea-statistik public-geodata-inventory","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=20) as response:
            raw=response.read(2000000)
            if len(raw)>=2000000:raise ValueError("Response exceeds 2MB")
            return {"ok":True,"data":json.loads(raw.decode("utf-8"))}
    except Exception as e:return {"ok":False,"error":str(e)[:220]}
def main():
    checked=[];candidates=[];visited=set()
    def scan(folder,depth=0):
        if depth>2 or folder in visited or len(visited)>70:return
        visited.add(folder)
        url=BASE+("/"+folder if folder else "")+"?f=pjson"
        response=get(url)
        checked.append({"folder":folder,"ok":response["ok"],"error":response.get("error")})
        if not response["ok"]:return
        data=response["data"]
        if "error" in data:
            checked[-1]["error"]=str(data["error"])[:200]
            return
        for f in data.get("folders",[]):
            if depth==0 or any(t in f.casefold() for t in TARGETS):
                scan((folder+"/" if folder else "")+f,depth+1)
        for service in data.get("services",[]):
            name=service.get("name","");kind=service.get("type","")
            if not any(t in name.casefold() for t in TARGETS) and not any(x in name.casefold() for x in ("gata","väg","trafik","samhall","samhälle","park")):continue
            info=get(BASE+"/"+name+"/"+kind+"?f=pjson")
            layers=[]
            if info["ok"] and "error" not in info["data"]:
                for layer in info["data"].get("layers",[]):
                    lname=layer.get("name","")
                    layers.append({"id":layer.get("id"),"name":lname})
            candidates.append({"name":name,"type":kind,"url":BASE+"/"+name+"/"+kind,"metadata_accessible":info["ok"] and "error" not in info.get("data",{}),"layers":layers})
    scan("")
    status="catalog_accessible" if checked and checked[0]["ok"] and not checked[0].get("error") else "catalog_unavailable"
    result={"checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":status,
      "scope":"Public ArcGIS metadata inventory only, targeted at Farligt gods, Parkering, Vaghallare and transport. No object extraction.",
      "portal":"https://kartportal.lulea.se/portal/apps/mapviewer/index.html",
      "map_source":"https://kartor.lulea.se/kommunkarta/",
      "confirmed_map_layer_names":["Farligt gods","Parkering","Väghållare"],
      "checked":checked,"candidate_services":candidates}
    output=Path("nvdb_output/lulea_transport_layer_inventory.json");output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(status, "folders",len(checked),"candidate services",len(candidates))
if __name__=="__main__":main()
