from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

START="https://kartor.lulea.se/kommunkarta/?layers=kollektivtrafik"

def fetch(url):
    req=Request(url,headers={"User-Agent":"pendling-transport-lulea/1.0"})
    with urlopen(req,timeout=120) as r:
        raw=r.read()
        enc=r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc,errors="replace"), r.geturl(), r.headers.get("content-type","")

def main():
    html,final_url,ctype=fetch(START)
    assets=[]
    for m in re.finditer(r'''(?:src|href)=["']([^"']+)["']''',html,re.I):
        href=m.group(1)
        if href.lower().endswith((".js",".json",".config")) or ".js?" in href.lower():
            assets.append(urljoin(final_url,href))
    assets=list(dict.fromkeys(assets))

    hits=[]
    patterns=[
        "kollektivtrafik","hållplats","hallplats","buss","MapServer","FeatureServer",
        "arcgis/rest","services/","wms","wfs","geoserver"
    ]
    def scan(url,text):
        lines=text.splitlines()
        for i,line in enumerate(lines,1):
            low=line.lower()
            if any(p.lower() in low for p in patterns):
                hits.append({"url":url,"line":i,"text":line[:1500]})

    scan(final_url,html)
    fetched=[]
    for url in assets[:80]:
        try:
            text,u,ct=fetch(url)
            fetched.append({"url":u,"content_type":ct,"size":len(text)})
            scan(u,text)
        except Exception as e:
            fetched.append({"url":url,"error":repr(e)})

    out={
        "start":START,
        "final_url":final_url,
        "html_size":len(html),
        "assets":fetched,
        "hits":hits,
    }
    Path("data").mkdir(exist_ok=True)
    Path("data/lulea_collective_map_inspect.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps({"assets":len(fetched),"hits":hits[:80]},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
