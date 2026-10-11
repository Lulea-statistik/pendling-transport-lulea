#!/usr/bin/env python3
"""Fetch municipality light/heavy truck stock from SCB, fail closed on unrecognized definitions."""
import json,urllib.request
from pathlib import Path
URL="https://api.scb.se/OV0104/v1/doris/sv/ssd/TK/TK1001/TK1001A/FordonTrafik"
M={"2580":"Luleå","2582":"Boden","2581":"Piteå","2514":"Kalix","2560":"Älvsbyn"}
def api(payload=None):
    headers={"User-Agent":"Lulea-statistik public analysis","Accept":"application/json"}
    if payload is None:req=urllib.request.Request(URL,headers=headers)
    else:req=urllib.request.Request(URL,headers={**headers,"Content-Type":"application/json"},data=json.dumps(payload).encode(),method="POST")
    with urllib.request.urlopen(req,timeout=90) as response:return json.load(response)
def main():
    meta=api();fields=meta["variables"]
    def get(needle):
        v=[x for x in fields if needle in x["code"].lower()]
        if len(v)!=1:raise ValueError("Ambiguous dimensions: "+needle+" "+str([x["code"] for x in fields]))
        return v[0]
    reg=get("region");vehicle=get("fordonsslag");year=get("år")
    regions=[str(k) for k in reg["values"] if str(k) in M]
    if len(regions)!=5:raise ValueError("Municipality identifiers missing")
    types={}
    for code,label in zip(vehicle["values"],vehicle["valueTexts"]):
        name=str(label).lower().strip()
        if name in ("lätt lastbil","lätta lastbilar"):types["light"]=str(code)
        if name in ("tung lastbil","tunga lastbilar"):types["heavy"]=str(code)
    if set(types)!={"light","heavy"}:raise ValueError("Truck type labels not found: "+str(vehicle["valueTexts"]))
    years=[str(v) for v in year["values"] if str(v) in ("2024","2025")]
    if len(years)!=2:raise ValueError("Missing year")
    measures=[v for v in fields if v["code"]=="ContentsCode"]
    if len(measures)>1:raise ValueError("Multiple content dimensions")
    query=[{"code":reg["code"],"selection":{"filter":"item","values":regions}},
           {"code":vehicle["code"],"selection":{"filter":"item","values":list(types.values())}},
           {"code":year["code"],"selection":{"filter":"item","values":years}}]
    if measures:
        if len(measures[0]["values"])!=1:raise ValueError("Multiple stock measures; inspect before querying")
        query.append({"code":"ContentsCode","selection":{"filter":"item","values":measures[0]["values"]}})
    result=api({"query":query,"response":{"format":"json"}})
    codes=[c["code"] for c in result["columns"]]
    col={code:codes.index(code) for code in (reg["code"],vehicle["code"],year["code"])}
    if len(result["data"])!=20:raise ValueError("Wrong cell count "+str(len(result["data"])))
    rows=[]
    for d in result["data"]:
        key=d["key"]
        region=str(key[col[reg["code"]]])
        code=str(key[col[vehicle["code"]]])
        kind=next((k for k,v in types.items() if v==code),None)
        value=str(d["values"][0])
        if kind is None or region not in M:raise ValueError("Unexpected record")
        number=None if value in (":","..","-","") else int(float(value))
        if number is not None and number<0:raise ValueError("Negative stock")
        rows.append({"kommun_code":region,"kommun":M[region],"year":str(key[col[year["code"]]]),"kind":kind,"count":number})
    out={"status":"source_data","source":"SCB TK1001A FordonTrafik","url":"https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__TK__TK1001__TK1001A/FordonTrafik/","definition":"Lastbilar i trafik, registrerade på respektive kommun vid årsslut; alla drivmedel. Ej antal dieselbilar eller antal som tankar i kommunen.","rows":rows}
    path=Path("docs/data/freight-truck-stock.json");path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Validated",len(rows),"truck stock cells")
if __name__=="__main__":main()
