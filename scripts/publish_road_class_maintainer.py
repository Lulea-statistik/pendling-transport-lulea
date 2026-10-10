#!/usr/bin/env python3
"""Validate the road-class-by-maintainer QA artifact before public JSON publication."""
import json
from pathlib import Path

source=Path("nvdb_output/nvdb_road_class_maintainer_qa.json")
data=json.loads(source.read_text(encoding="utf-8"))
if data.get("status")!="qa_only":raise ValueError("Unexpected QA status")
municipalities=data.get("municipalities",{})
if set(municipalities)!={"2580","2581","2582","2514","2560"}:raise ValueError("Unexpected geography")
categories=("statlig","kommunal","enskild")
out={}
for code,item in municipalities.items():
    total=item["car_network_unique_km"]
    if total<=0:raise ValueError("Empty road network "+code)
    if item["cross_class_overlap_km"]>0.01:raise ValueError("Cross-class overlap "+code)
    if item["conflicting_manager_sum_km"]>0.01:raise ValueError("Conflicting maintainers "+code)
    if item["unmatched_manager_sum_km"]/total>0.02:raise ValueError("Low maintainer coverage "+code)
    if abs(total-item["class_sum_km"])>0.03:raise ValueError("Class total mismatch "+code)
    if abs(total-item["manager_assigned_sum_km"]-item["unmatched_manager_sum_km"])>0.04:raise ValueError("Maintainer total mismatch "+code)
    classes={}
    for cl,values in item["road_class_by_maintainer"].items():
        if not cl.isdigit() or not 0<=int(cl)<=9:raise ValueError("Invalid road class")
        km=values["car_road_unique_km"]
        splits={name:values["maintainer_km"].get(name,0) for name in categories}
        splits["okand"]=values["not_classified_km"]
        if abs(km-sum(splits.values()))>0.015:raise ValueError("Class by maintainer discrepancy "+code+" "+cl)
        classes[cl]={"total_km":km,"km":splits}
    if abs(sum(v["total_km"] for v in classes.values())-total)>0.04:
        raise ValueError("Network sum mismatch "+code)
    out[code]={"name":item["name"],"car_network_km":total,
               "unmatched_km":item["unmatched_manager_sum_km"],"classes":classes}
destination=Path("docs/data/nvdb-road-class-maintainer.json")
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps({
   "status":"preliminary_validated","source":"Trafikverket NVDB Lastkajen Norrbottens län paket 10155",
   "method":"NVDB funktionell vägklass 0–9 × väghållartyp; exakt geografiskt sammanfallande linjegeometri i EPSG:3006; unika längder per klass; omatchat särredovisas.",
   "caveat":"Ingen kontroll av samtliga nästan sammanfallande väggeometrier, separata körbanor eller fullständig vägnätstopologi. Längderna är preliminära; FA-summa är summa av fem kommunala utklipp.",
   "municipalities":out},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Validated road class by maintainer:",len(out),"municipalities")
