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

def main():
    Path("data").mkdir(exist_ok=True)
    queries={
      "kommun":"t1004|kommun",
      "metrics":"t1004|antolyckdsl|antpersd|antperss|antpersl|antdslper100000|ar|kommun",
      "base":"t1004|antolyckdsl|antpersd|antperss|antpersl|antdslper100000|ar",
    }
    out={}
    for k,q in queries.items():
        text=get("/structure?query="+quote(q,safe="|:,"))
        out[k]=json.loads(text)
    Path("data/trafa_injury_query_structures.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["kommun"],ensure_ascii=False)[:12000])

if __name__=="__main__":
    main()
