#!/usr/bin/env python3
"""Publish checked class-wise width bands from the same-run NVDB QA artifact."""
import json,base64,os,urllib.request,urllib.error
from pathlib import Path
p=Path("nvdb_output/nvdb_road_width_lanes_qa.json")
qa=json.loads(p.read_text(encoding="utf-8"))
if qa.get("status")!="qa_only":raise ValueError("Unexpected analysis status")
municipalities=qa["municipalities"]
if set(municipalities)!={"2580","2582","2581","2514","2560"}:raise ValueError("Unexpected municipalities")
bands=("<4 m","4–<6 m","6–<8 m","8–<10 m","≥10 m")
result={}
for code,m in municipalities.items():
    stats={}
    for c,detail in m["variables"]["width"].items():
        if c not in map(str,range(10)):raise ValueError("Unknown road class")
        observed={key:detail["bands_km"].get(key,0) for key in bands}
        known=detail["known_km"]
        if any(x<0 for x in observed.values()):raise ValueError("Negative lengths")
        if detail["multiple_attribute_km"]>0.01:raise ValueError("Overlapping width classes "+code+" "+c)
        if abs(sum(observed.values())-known)>0.015:raise ValueError("Width-band sum mismatch "+code+" "+c)
        if known>detail["class_km"]+0.01:raise ValueError("Coverage exceeds road length")
        if abs(detail["class_km"]-known-detail["no_attribute_km"])>0.015:raise ValueError("Missing lengths mismatch")
        stats[c]={"road_km":detail["class_km"],"known_km":known,"bands_km":observed}
    if abs(sum(x["road_km"] for x in stats.values())-m["car_network_km"])>0.05:raise ValueError("Municipal network mismatch "+code)
    result[code]={"name":m["name"],"classes":stats}
payload={"status":"validated_preliminary","source":"Trafikverket NVDB Lastkajen Norrbotten",
         "method":"EPSG:3006 exact line coincidence, function road class x road width; width ranges in meters; rounded kilometers.",
         "limitations":"Observed subset, NOT a representative sample of all road lengths, especially lower function classes. No interpolation; unknown does not mean narrow.",
         "municipalities":result}
path=Path("docs/data/nvdb-road-width-by-class.json")
path.parent.mkdir(exist_ok=True,parents=True)
path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
token=os.environ.get("GH_TOKEN")
if not token:
    print("Validated locally; no GitHub token")
else:
    api="https://api.github.com/repos/"+os.environ["GITHUB_REPOSITORY"]+"/contents/"+str(path)
    headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","Content-Type":"application/json"}
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(api,headers=headers),timeout=30) as resp:
                sha=json.load(resp)["sha"]
        except urllib.error.HTTPError as err:
            if err.code!=404:raise
            sha=None
        data={"message":"Update verified road width by functional class","content":base64.b64encode(path.read_bytes()).decode()}
        if sha:data["sha"]=sha
        try:
            with urllib.request.urlopen(urllib.request.Request(api,headers=headers,data=json.dumps(data).encode(),method="PUT"),timeout=30) as resp:
                print("Published",resp.status)
            break
        except urllib.error.HTTPError as err:
            if err.code not in (409,422) or i==3:raise
print("Validated",len(result),"municipalities")
