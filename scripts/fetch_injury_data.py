from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

API="https://api.trafa.se/api/data"
CODES=["2505","2506","2510","2513","2514","2518","2521","2523","2560","2580","2581","2582","2583","2584"]
YEARS=[str(y) for y in range(2020,2026)]
SPEEDS=["030","040","050","060","070","080","090","100","110","120","999"]
ROAD_TYPES=["1","10","11","12","13","2","3","4","5","6","9"]

def get(query):
    url=API+"?query="+quote(query,safe="|:,")+"&lang=sv"
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0","Accept":"application/json"})
    with urlopen(req,timeout=180) as r:
        return json.loads(r.read().decode(r.headers.get_content_charset() or "utf-8",errors="replace"))

def parse_num(value):
    if value is None:
        return None
    s=str(value).strip().replace(" ","").replace(",",".")
    if s in {"","..","."}:
        return None
    if s in {"–","-"}:
        return 0
    try:
        n=float(s)
        return int(n) if n.is_integer() else n
    except ValueError:
        return None

def rows(obj):
    result=[]
    for r in obj.get("Rows",[]) or []:
        rec={}
        labels={}
        for c in r.get("Cell",[]) or []:
            col=c.get("Column")
            if c.get("IsMeasure"):
                rec[col]=parse_num(c.get("Value"))
            else:
                rec[col]=c.get("Name")
                labels[col]=c.get("FormattedValue") or c.get("Value")
        rec["_labels"]=labels
        result.append(rec)
    return result

def main():
    base="t1004|antolyckdsl|antpersd|antperss|antpersl|antdslper100000"
    latest="2025"

    total=[]
    speed=[]
    road=[]
    for code in CODES:
        q_tot=base+"|ar:"+",".join(YEARS)+"|lan:25|kommun:"+code
        total.extend(rows(get(q_tot)))

        q_speed="t1004|antolyckdsl|antpersd|antperss|antpersl|ar:"+latest+"|hastighet:"+",".join(SPEEDS)+"|lan:25|kommun:"+code
        speed.extend(rows(get(q_speed)))

        q_road="t1004|antolyckdsl|antpersd|antperss|antpersl|ar:"+latest+"|vagtyp:"+",".join(ROAD_TYPES)+"|lan:25|kommun:"+code
        road.extend(rows(get(q_road)))

        print(code,"total",len([r for r in total if str(r.get("kommun"))==code]),
              "speed",len([r for r in speed if str(r.get("kommun"))==code]),
              "road",len([r for r in road if str(r.get("kommun"))==code]))

    out={
        "source":"Trafikanalys API",
        "product":"Vägtrafikskador",
        "api_product":"t1004",
        "years":[int(x) for x in YEARS],
        "latest_year":int(latest),
        "total":total,
        "by_speed_limit":speed,
        "by_road_type":road,
    }

    for p in [Path("data/injuries.json"),Path("docs/data/injuries.json")]:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("total",len(total),"speed",len(speed),"road",len(road))

if __name__=="__main__":
    main()
