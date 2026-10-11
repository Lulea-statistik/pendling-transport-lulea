#!/usr/bin/env python3
"""SCB EN0109 2024-2025 reseller fuel deliveries. Never equate deliveries to truck fuel consumption."""
import json,os,re,urllib.request
from pathlib import Path

URL="https://api.scb.se/OV0104/v1/doris/sv/ssd/EN/EN0109/EN0109A/LevBrTypKom"
COMMUNER={"2580":"Luleå","2582":"Boden","2581":"Piteå","2514":"Kalix","2560":"Älvsbyn"}
def api(payload=None):
    headers={"User-Agent":"Lulea-statistik/open-statistics (public Github project)","Accept":"application/json"}
    request=urllib.request.Request(URL,headers=headers)
    if payload is not None:
        request=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={**headers,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(request,timeout=75) as resp:return json.load(resp)
def variable(meta,needle):
    arr=[v for v in meta["variables"] if needle in v["code"].lower()]
    if len(arr)!=1:raise ValueError("Expected exactly one "+needle+" field, got "+str([v["code"] for v in meta["variables"]]))
    return arr[0]
def select_codes(field,targets):
    found=[]
    for code,text in zip(field["values"],field["valueTexts"]):
        if str(code) in targets or any(str(text).strip().startswith(code+" ") for code in targets):
            found.append(str(code))
    return sorted(set(found))
def main():
    meta=api()
    region=variable(meta,"region");fuel=variable(meta,"bransle");year=variable(meta,"tid")
    selected_regions=select_codes(region,COMMUNER)
    if len(selected_regions)!=5:raise ValueError("Expected five FA municipalities, got "+str(selected_regions))
    diesel=[str(code) for code,label in zip(fuel["values"],fuel["valueTexts"]) if "diesel" in str(label).lower()]
    if len(diesel)!=1:raise ValueError("Diesel fuel definition is ambiguous: "+str(list(zip(fuel["values"],fuel["valueTexts"]))))
    years=[str(y) for y in year["values"] if str(y) in ("2024","2025")]
    if not years:raise ValueError("Missing 2024/2025")
    query={"query":[{"code":region["code"],"selection":{"filter":"item","values":selected_regions}},
                    {"code":fuel["code"],"selection":{"filter":"item","values":diesel}},
                    {"code":year["code"],"selection":{"filter":"item","values":years}},
                    {"code":"ContentsCode","selection":{"filter":"item","values":next(v["values"] for v in meta["variables"] if v["code"]=="ContentsCode")}}],
            "response":{"format":"json"}}
    raw=api(query)
    columns=[x["code"] for x in raw["columns"]]
    expected={region["code"],fuel["code"],year["code"],"ContentsCode"} | set(next(v["values"] for v in meta["variables"] if v["code"]=="ContentsCode"))
    extra=[c for c in columns if c not in expected and c.lower() not in ("contentscode","contents")]
    if extra:raise ValueError("Unexpected dimensions "+str(extra))
    if len(raw["data"])!=5*len(years):raise ValueError("Unexpected response length, or multiple contents measures")
    index={c:i for i,c in enumerate(columns)}
    rows=[]
    for obj in raw["data"]:
        key=obj["key"];count=obj["values"][0]
        # SCB uses '..' and ':' for unavailable/confidential data; do not convert to zero.
        if str(count).strip() in ("..",":","-",""):value=None
        else:
            try:value=float(str(count).replace(" ","").replace(",","."))
            except ValueError:raise ValueError("Unexpected numeric cell "+str(count))
            if value<0:raise ValueError("Negative fuel delivery")
        code=str(key[index[region["code"]]])
        if code not in COMMUNER:raise ValueError("Unexpected municipality "+code)
        rows.append({"kommun_code":code,"kommun":COMMUNER[code],"year":str(key[index[year["code"]]]),"diesel_m3":value})
    if len(rows)!=5*len(years):raise ValueError("Unexpected number of municipality-year cells "+str(len(rows)))
    target=Path("docs/data/freight-diesel-reseller-deliveries.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({"status":"source_data","source":"SCB EN0109 LevBrTypKom",
        "source_url":"https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__EN__EN0109__EN0109A/LevBrTypKom/",
        "unit":"m3","scope":"Bränsleleveranser till återförsäljare per kommun, inte observerad tankning eller lastbilsspecifik förbrukning.",
        "comparability":"2024–2025 separat tabell; ej direkt hopkopplad med 2018–2023.",
        "fuel_code":diesel[0],"fuel_label":fuel["valueTexts"][fuel["values"].index(diesel[0])],
        "rows":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Verified diesel reseller deliveries",len(rows),"cells",sum(x["diesel_m3"] is None for x in rows),"missing")
if __name__=="__main__":main()
