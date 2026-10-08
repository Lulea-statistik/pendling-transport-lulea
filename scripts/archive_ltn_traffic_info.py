from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

URL="https://lanstrafikennorrbotten.se/trafikinformation"
JSON_PATH=Path("data/traffic_disruptions.json")
CSV_PATH=Path("data/traffic_disruptions.csv")
WEB_PATH=Path("docs/data/traffic_disruptions.json")

def fetch_html():
    req=Request(URL,headers={"User-Agent":"pendling-transport-lulea/1.0"})
    with urlopen(req,timeout=120) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8",errors="replace")

def clean(text):
    return re.sub(r"\s+"," ",text or "").strip()

def extract_section(soup, heading_text):
    lines=[clean(x) for x in soup.stripped_strings]
    lines=[x for x in lines if x]
    try:
        start=next(i for i,x in enumerate(lines) if x.casefold()==heading_text.casefold())+1
    except StopIteration:
        return []

    stop_names={"aktuella","planerade","prenumerera på trafikinformation","länstrafiken norrbotten"}
    end=len(lines)
    for i in range(start,len(lines)):
        if lines[i].casefold() in stop_names and lines[i].casefold()!=heading_text.casefold():
            end=i
            break
    section=lines[start:end]

    out=[]
    i=0
    while i<len(section)-1:
        title=section[i]
        if i+1<len(section) and section[i+1].casefold()=="visa":
            j=i+2
            body_parts=[]
            while j<len(section):
                if j+1<len(section) and section[j+1].casefold()=="visa":
                    break
                body_parts.append(section[j])
                j+=1
            body=clean(" ".join(body_parts))
            key=hashlib.sha1((heading_text+"|"+title).encode("utf-8")).hexdigest()[:16]
            line_nums=sorted(set(re.findall(r"(?i)linje\\s+(\\d+)",title+" "+body)))
            out.append({
                "id":key,
                "status":heading_text,
                "title":title,
                "body":body,
                "lines":line_nums,
            })
            i=j
        else:
            i+=1
    return out

def load_existing():
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"source":URL,"updated":None,"items":[]}

def main():
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    soup=BeautifulSoup(fetch_html(),"html.parser")
    current=extract_section(soup,"Aktuella")
    planned=extract_section(soup,"Planerade")
    live=current+planned
    if not live:
        lines=[clean(x) for x in soup.stripped_strings]
        for i,x in enumerate(lines):
            if "Aktuella" in x or "Planerade" in x or x=="Visa":
                print("DEBUG",i,lines[max(0,i-3):i+8])

    existing=load_existing()
    by_id={x["id"]:x for x in existing.get("items",[])}
    live_ids={x["id"] for x in live}

    for item in live:
        old=by_id.get(item["id"])
        if old:
            old.update(item)
            old["last_seen"]=now
            old["active"]=True
        else:
            item["first_seen"]=now
            item["last_seen"]=now
            item["active"]=True
            by_id[item["id"]]=item

    for item in by_id.values():
        if item["id"] not in live_ids:
            item["active"]=False

    items=sorted(by_id.values(),key=lambda x:(not x.get("active",False),x.get("first_seen","")),reverse=False)
    out={
        "source":URL,
        "updated":now,
        "active_count":sum(1 for x in items if x.get("active")),
        "history_count":len(items),
        "items":items,
    }

    JSON_PATH.parent.mkdir(parents=True,exist_ok=True)
    WEB_PATH.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(out,ensure_ascii=False,indent=2)
    JSON_PATH.write_text(text,encoding="utf-8")
    WEB_PATH.write_text(text,encoding="utf-8")

    with CSV_PATH.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id","status","title","body","lines","first_seen","last_seen","active"])
        w.writeheader()
        for x in items:
            row=x.copy()
            row["lines"]=";".join(row.get("lines",[]))
            w.writerow({k:row.get(k,"") for k in w.fieldnames})

    print("active",out["active_count"],"history",out["history_count"])
    for x in live[:10]:
        print(x["status"],x["title"])

if __name__=="__main__":
    main()
