from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE="https://api.trafa.se/api/structure"

def get(url):
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0","Accept":"application/json"})
    with urlopen(req,timeout=120) as r:
        raw=r.read()
        charset=r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset,errors="replace")

def main():
    text=get(BASE)
    Path("data").mkdir(exist_ok=True)
    Path("data/trafa_structure_all.json").write_text(text,encoding="utf-8")
    product_text=get(BASE+"?query=t1004")
    Path("data/trafa_injury_structure.json").write_text(product_text,encoding="utf-8")
    try:
        obj=json.loads(text)
    except Exception:
        print(text[:5000])
        return

    # Flatten product-like nodes and print items mentioning road traffic injuries.
    hits=[]
    def walk(x,path=""):
        if isinstance(x,dict):
            blob=" ".join(str(v) for v in x.values() if not isinstance(v,(dict,list))).lower()
            if any(term in blob for term in ["vägtrafikskad","vagtrafikskad","traffic injur","skadade","omkomna"]):
                hits.append({"path":path,"item":x})
            for k,v in x.items():
                walk(v,path+"/"+str(k))
        elif isinstance(x,list):
            for i,v in enumerate(x):
                walk(v,path+f"/{i}")
    walk(obj)
    Path("data/trafa_injury_hits.json").write_text(json.dumps(hits,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(hits[:50],ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
